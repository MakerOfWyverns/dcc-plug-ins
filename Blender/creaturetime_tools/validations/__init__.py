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

class Validation(object):
    NAME = None

    def __init__(self):
        self.__errors = []

    def reset(self):
        self.__errors.clear()

    def validate(self, context, scene):
        raise NotImplementedError()

    def warning(self, message, repair_func=None, repair_context=None):
        self.__add_error(False, message, repair_func, repair_context)

    def error(self, message, repair_func=None, repair_context=None):
        self.__add_error(True, message, repair_func, repair_context)

    def __add_error(self, error_type, message, repair_func, repair_context):
        self.__errors.append((error_type, message, (repair_func, repair_context) if repair_func else None))

    def has_errors(self):
        return bool(self.__errors)

    def iter_errors(self):
        for error in self.__errors:
            yield error

    def has_repair(self, index):
        return bool(self.__errors[index][2])

    def repair(self, index):
        _, _, repair = self.__errors[index]
        if repair:
            repair_func, repair_context = repair
            return repair_func(repair_context)
        return False


class MeshNamesValidation(Validation):
    NAME = 'Mesh Names'

    @staticmethod
    def repair_names(context):
        mesh, obj = context
        mesh.name = obj.name
        return True

    def validate(self, context, scene):
        for obj in bpy.data.objects:
            if not isinstance(obj.data, bpy.types.Mesh):
                continue

            mesh = obj.data
            if obj.name != mesh.name:
                self.error(
                    'Mesh name (%s) did not match object name (%s)' % (mesh.name, obj.name),
                    MeshNamesValidation.repair_names, (mesh, obj))


# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------

class CREATURETIME_OT_ValidationActions(Operator):
    """Performs validation actions"""

    bl_idname = "creaturetime.validation_actions"
    bl_label = "Validation Actions"
    bl_description = "Run Validation"
    bl_options = {'REGISTER'}

    action: bpy.props.EnumProperty(
        items=(
            ('VALIDATE', "Validate", ""),
        )
    )

    @classmethod
    def poll(cls, context):
        wm = bpy.context.window_manager
        try:
            wm.validations[wm.validations_index]
        except IndexError:
            return False
        else:
            return True

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        if self.action == 'VALIDATE':
            try:
                item = wm.validations[wm.validations_index]
            except IndexError:
                pass
            else:
                # Clear out previous errors
                wm.errors.clear()

                # Run Validation
                validation = validations[item.id]
                validation.reset()
                validation.validate(context, wm)

                # Populate errors/warnings
                if validation.has_errors():
                    error_icon_id = resources.get('error_x16').icon_id
                    warning_icon_id = resources.get('warning_x16').icon_id
                    for index, (error_type, message, repair) in enumerate(validation.iter_errors()):
                        error_item = wm.errors.add()
                        error_item.name = message
                        error_item.icon_value = error_icon_id if error_type else warning_icon_id
                        error_item.validation_id = item.id
                        error_item.error_id = index

        return {"FINISHED"}


class CREATURETIME_OT_ErrorActions(Operator):
    """Performs validation actions"""

    bl_idname = "creaturetime.validation_repair"
    bl_label = "Repair Action"
    bl_description = "Repair Action"
    bl_options = {'REGISTER'}

    action: bpy.props.EnumProperty(
        items=(
            ('REPAIR', "Repair", ""),
        )
    )

    @classmethod
    def poll(cls, context):
        wm = bpy.context.window_manager
        try:
            item = wm.errors[wm.errors_index]
        except IndexError:
            return False
        else:
            validation = validations[item.validation_id]
            return validation.has_repair(item.error_id)

    def invoke(self, context, event):
        wm = bpy.context.window_manager
        if self.action == 'REPAIR':
            try:
                item = wm.errors[wm.errors_index]
            except IndexError:
                pass
            else:
                validation = validations[item.validation_id]
                if validation.has_repair(item.error_id):
                    if validation.repair(item.error_id):
                        wm.errors.remove(wm.errors_index)
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


class CREATURETIME_PT_Validations(Panel):
    """Validations panel."""

    bl_idname = 'creaturetime.validations_panel'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'Validations'
    bl_label = "Validations"

    def draw(self, context):
        layout = self.layout
        wm = bpy.context.window_manager

        rows = 2
        layout.label(text="Validations")
        row = layout.row()
        row.template_list(CREATURETIME_UL_Validations.__name__, "", wm, "validations", wm, "validations_index",
                          rows=rows)

        col = row.column(align=True)
        col.operator(CREATURETIME_OT_ValidationActions.bl_idname, icon_value=resources.get('validate_x16').icon_id, text="").action = 'VALIDATE'

        rows = 2
        layout.label(text="Errors")
        row = layout.row()
        row.template_list(CREATURETIME_UL_Errors.__name__, "", wm, "errors", wm, "errors_index", rows=rows)

        col = row.column(align=True)
        col.operator(CREATURETIME_OT_ErrorActions.bl_idname, icon_value=resources.get('repair_x16').icon_id, text="").action = 'REPAIR'


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
    CREATURETIME_OT_ValidationActions,
    CREATURETIME_OT_ErrorActions,
    CREATURETIME_UL_Validations,
    CREATURETIME_Validation,
    CREATURETIME_UL_Errors,
    CREATURETIME_Error,
    CREATURETIME_PT_Validations,
)

# Store all validations
# TODO: Make this discoverable.
validations = (
    MeshNamesValidation(),
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
    wm.validations_index = IntProperty()
    wm.errors = CollectionProperty(type=CREATURETIME_Error)
    wm.errors_index = IntProperty()

    bpy.app.handlers.load_post.append(load_validations)


def unregister():
    bpy.app.handlers.load_post.remove(load_validations)

    # Tear down scene properties
    wm = bpy.types.WindowManager
    del wm.validations
    del wm.validations_index
    del wm.errors
    del wm.errors_index

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
