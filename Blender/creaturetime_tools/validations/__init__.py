import bpy

from bpy.props import (IntProperty,
                       BoolProperty,
                       StringProperty,
                       CollectionProperty,
                       PointerProperty)

from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList)

from bpy.app.handlers import persistent

from .. import resources


# -------------------------------------------------------------------
#   Validations
# -------------------------------------------------------------------

def ct_id(name):
    return f'creaturetime.{name}'


class Validation(object):
    NAME = None

    def __init__(self):
        self.__errors = {}

    def reset(self):
        self.__errors.clear()

    def validate(self, context, scene):
        raise NotImplementedError()

    def warning(self, message, repair_func=None, repair_context=None):
        self.__add_error(False, message, repair_func, repair_context)

    def error(self, message, repair_func=None, repair_context=None):
        self.__add_error(True, message, repair_func, repair_context)

    def __add_error(self, error_type, message, repair_func, repair_context):
        if not isinstance(repair_context, tuple):
            repair_context = (repair_context,)
        self.__errors[len(self.__errors)] = (error_type, message, (repair_func, repair_context) if repair_func else None)

    def has_errors(self):
        return bool(self.__errors)

    def iter_errors(self):
        for error_id in self.__errors:
            error_type, message, repair = self.__errors[error_id]
            yield error_id, error_type, message, repair

    def has_repair(self, error_id):
        return bool(self.__errors[error_id][2])

    def repair(self, error_id):
        _, _, repair = self.__errors[error_id]
        if repair:
            repair_func, repair_context = repair
            return repair_func(repair_context)
        return False


class ObjectNamesValidation(Validation):
    NAME = 'Object => Data Names'

    @staticmethod
    def repair_names(context):
        data, obj = context
        data.name = obj.name
        return True

    def validate(self, context, scene):
        for obj in bpy.data.objects:
            if not isinstance(obj.data, (bpy.types.Mesh, bpy.types.Armature)):
                continue

            mesh = obj.data
            if obj.name != mesh.name:
                self.error(
                    'Name (%s) did not match object name (%s)' % (mesh.name, obj.name),
                    ObjectNamesValidation.repair_names, (mesh, obj))


class BoneNamesValidation(Validation):
    NAME = 'Bone Names'

    @staticmethod
    def repair_names(context):
        bone = context[0]
        name = bone.name
        if ':' in name:
            name = name[name.rfind(':') + 1:]
        if 'Left' in name:
            name = name.replace('Left', '')
            name += '_L'
        if 'Right' in name:
            name = name.replace('Right', '')
            name += '_R'
        if ' ' in name:
            name = name.replace(' ', '')
        bone.name = name

        return True

    def validate(self, context, scene):
        for obj in bpy.data.objects:
            if not isinstance(obj.data, bpy.types.Armature):
                continue

            error_msg = 'Bone name (%s) needs to have correct naming convention'

            armature = obj.data
            for bone in armature.bones:
                if ':' in bone.name:
                    self.error(error_msg % bone.name, BoneNamesValidation.repair_names, bone)
                    continue

                if ' ' in bone.name:
                    self.error(error_msg % bone.name, BoneNamesValidation.repair_names, bone)
                    continue

                if 'Left' in bone.name:
                    self.error(error_msg % bone.name, BoneNamesValidation.repair_names, bone)
                    continue

                if 'Right' in bone.name:
                    self.error(error_msg % bone.name, BoneNamesValidation.repair_names, bone)
                    continue


# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------


def validate_item(context, wm, item, validation):
    validation.reset()
    validation.validate(context, wm)

    # Populate errors/warnings
    if validation.has_errors():
        error_icon_id = resources.get('error_x16').icon_id
        warning_icon_id = resources.get('warning_x16').icon_id
        for (error_id, error_type, message, repair) in validation.iter_errors():
            error_item = wm.errors.add()
            error_item.name = message
            error_item.icon_value = error_icon_id if error_type else warning_icon_id
            error_item.validation_id = item.id
            error_item.error_id = error_id


class CREATURETIME_OT_ValidateAllActions(Operator):
    """Performs validation on all validation"""

    bl_idname = ct_id('validation_validate_all')
    bl_label = "Validate All"
    bl_description = "Run all validations"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        wm = bpy.context.window_manager
        for item in wm.validations:
            if item.validate:
                return True
        return False

    def invoke(self, context, event):
        wm = bpy.context.window_manager

        # Clear out previous errors
        wm.errors.clear()

        for idx, item in enumerate(wm.validations):
            if not item.validate:
                continue
            validation = validations[idx]
            validate_item(context, wm, item, validation)

        return {"FINISHED"}


class CREATURETIME_OT_ValidateActions(Operator):
    """Performs validation on selected validation"""

    bl_idname = ct_id('validation_validate')
    bl_label = "Validate"
    bl_description = "Run selected validation"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        wm = bpy.context.window_manager
        try:
            wm.validations[wm.validation_index]
        except IndexError:
            return False
        else:
            return True

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        try:
            item = wm.validations[wm.validation_index]
        except IndexError:
            pass
        else:
            # Clear out previous errors
            wm.errors.clear()

            # Run Validation
            validation = validations[item.id]
            validate_item(context, wm, item, validation)

        return {"FINISHED"}


class CREATURETIME_OT_RepairAllActions(Operator):
    """Performs repair on selected error"""

    bl_idname = ct_id('validation_repair_all')
    bl_label = "Repair All"
    bl_description = "Repair all errors"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        wm = bpy.context.window_manager
        for item in wm.errors:
            validation = validations[item.validation_id]
            if validation.has_repair(item.error_id):
                return True
        return False

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        to_remove = []
        for index, item in enumerate(wm.errors):
            validation = validations[item.validation_id]
            if validation.has_repair(item.error_id):
                if validation.repair(item.error_id):
                    to_remove.insert(0, index)
                    continue
            index += 1

        for index in to_remove:
            wm.errors.remove(index)

        return {"FINISHED"}


class CREATURETIME_OT_RepairActions(Operator):
    """Performs repair on selected error"""

    bl_idname = ct_id('validation_repair')
    bl_label = "Repair"
    bl_description = "Repair selected error"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        wm = bpy.context.window_manager
        try:
            item = wm.errors[wm.error_index]
        except IndexError:
            return False
        else:
            validation = validations[item.validation_id]
            return validation.has_repair(item.error_id)

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        try:
            item = wm.errors[wm.error_index]
        except IndexError:
            pass
        else:
            validation = validations[item.validation_id]
            if validation.has_repair(item.error_id):
                if validation.repair(item.error_id):
                    wm.errors.remove(wm.error_index)
                else:
                    raise Exception('Failed to repair - %s' % item.name)

        return {"FINISHED"}


# -------------------------------------------------------------------
#   Drawing
# -------------------------------------------------------------------

class CREATURETIME_UL_Validations(UIList):
    """Display validation."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        layout.prop(item, "validate", text='')
        layout.label(text=item.name)

    def invoke(self, context, event):
        pass


class CREATURETIME_UL_Errors(UIList):
    """Display errors."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        layout.label(text=item.name, icon_value=item.icon_value)

    def invoke(self, context, event):
        pass


class VIEW3D_PT_Validator(Panel):
    """Validations panel."""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = 'Validator'
    bl_category = 'CreatureTime'

    def draw(self, context):
        layout = self.layout
        wm = bpy.context.window_manager

        layout.label(text='Validations', icon_value=resources.get('validate_x16').icon_id)
        row = layout.row()
        row.template_list(CREATURETIME_UL_Validations.__name__,
                          'validations',
                          wm, 'validations',
                          wm, 'validation_index',
                          rows=3)

        col = row.column(align=True)
        col.operator(CREATURETIME_OT_ValidateAllActions.bl_idname,
                     text="",
                     icon_value=resources.get('validate_x16').icon_id)
        col.operator(CREATURETIME_OT_ValidateActions.bl_idname,
                     text="",
                     icon_value=resources.get('validate_x16').icon_id)

        layout.label(text='Errors', icon_value=resources.get('repair_x16').icon_id)
        row = layout.row()
        row.template_list(CREATURETIME_UL_Errors.__name__,
                          'validation_errors',
                          wm, 'errors',
                          wm, 'error_index',
                          rows=3)

        col = row.column(align=True)
        col.operator(CREATURETIME_OT_RepairAllActions.bl_idname,
                     text="",
                     icon_value=resources.get('repair_x16').icon_id)
        col.operator(CREATURETIME_OT_RepairActions.bl_idname,
                     text="",
                     icon_value=resources.get('repair_x16').icon_id)


# -------------------------------------------------------------------
#   Collection
# -------------------------------------------------------------------

class CREATURETIME_Validation(PropertyGroup):
    """Validation properties."""

    # name: StringProperty() -> Instantiated by default
    id: IntProperty(default=-1)
    validate: BoolProperty()


class CREATURETIME_Error(PropertyGroup):
    """Validation error properties."""

    # name: StringProperty() -> Instantiated by default
    validation_id: IntProperty(default=-1)
    error_id: IntProperty(default=-1)
    icon_value: IntProperty(default=-1)


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

# Store all classes to register
classes = (
    CREATURETIME_OT_ValidateAllActions,
    CREATURETIME_OT_ValidateActions,
    CREATURETIME_OT_RepairAllActions,
    CREATURETIME_OT_RepairActions,
    CREATURETIME_UL_Validations,
    CREATURETIME_Validation,
    CREATURETIME_UL_Errors,
    CREATURETIME_Error,
    VIEW3D_PT_Validator,
)

# Store all validations
# TODO: Make this discoverable.
validations = (
    ObjectNamesValidation(),
    BoneNamesValidation()
)


@persistent
def load_validations(*args, **kwargs):
    wm = bpy.context.window_manager
    wm.errors.clear()
    wm.validations.clear()
    for idx, validation in enumerate(validations):
        item = wm.validations.add()
        item.name = validation.NAME
        item.id = idx
        item.validate = True


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # Set up validation properties
    wm = bpy.types.WindowManager
    wm.validations = CollectionProperty(type=CREATURETIME_Validation)
    wm.validation_index = IntProperty(name='Active Validation Index')
    wm.errors = CollectionProperty(type=CREATURETIME_Error)
    wm.error_index = IntProperty(name='Active Error Index')

    bpy.app.handlers.load_post.append(load_validations)


def unregister():
    bpy.app.handlers.load_post.remove(load_validations)

    # Tear down scene properties
    wm = bpy.types.WindowManager
    del wm.validations
    del wm.validation_index
    del wm.errors
    del wm.error_index

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
