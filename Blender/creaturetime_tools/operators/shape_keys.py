
# Blender imports
import bpy

# CreatureTime imports
from . import common
from .. import resources

class _RemoveUnusedShapeKeys(bpy.types.Operator):
    """
    Delete Blend Shapes with no assigned weight of active object
    """

    bl_label = "Remove Unused Blend Shapes"
    bl_idname = "creaturetime.remove_unused_blend_shapes"
    bl_description = "Delete Blend Shapes with no assigned weight of active object."
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # Tolerance to small differences, change it if you want
    __Tolerance = 0.001

    @classmethod
    def poll(cls, context):
        return (context.mode == 'OBJECT' and
                context.object.data.shape_keys and
                context.object.data.shape_keys.use_relative)

    def execute(self, context):
        import numpy as np

        obj = context.object

        kbs = obj.data.shape_keys.key_blocks
        vertices = len(obj.data.vertices)
        to_delete = []

        # Cache locs for rel keys since many keys have the same rel key
        cache = {}

        locs = np.empty(3 * vertices, dtype=np.float32)

        for kb in kbs:
            if kb == kb.relative_key: continue

            kb.data.foreach_get("co", locs)

            if kb.relative_key.name not in cache:
                rel_locs = np.empty(3 * vertices, dtype=np.float32)
                kb.relative_key.data.foreach_get("co", rel_locs)
                cache[kb.relative_key.name] = rel_locs
            rel_locs = cache[kb.relative_key.name]

            locs -= rel_locs
            if (np.abs(locs) < _RemoveUnusedShapeKeys.__Tolerance).all():
                to_delete.append(kb.name)

        for kb_name in to_delete:
            obj.shape_key_remove(obj.data.shape_keys.key_blocks[kb_name])

        return {'FINISHED'}


class _ApplyShapeKeyAsBasis(bpy.types.Operator):
    """
    Applies current selected shape key to the basis.
    Credit goes to deprecated Cats Blender Plugin.
    """

    bl_label = "Apply Shape Key As Basis"
    bl_idname = "creaturetime.apply_shape_key_as_basis"
    bl_description = "Applies current selected shape key to the basis."
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.object.active_shape_key and context.object.active_shape_key_index > 0

    def execute(self, context):
        obj = context.object

        # Get shape key which will be the new basis
        new_basis_shape_key = obj.active_shape_key
        new_basis_shape_key_name = new_basis_shape_key.name
        new_basis_shape_key_value = new_basis_shape_key.value

        # Check for reverted shape keys
        if ' - Reverted' in new_basis_shape_key_name and new_basis_shape_key.relative_key.name != 'Basis':
            for shapekey in obj.data.shape_keys.key_blocks:
                if ' - Reverted' in shapekey.name and shapekey.relative_key.name == 'Basis':
                    # TODO: Include error message.
                    # Common.show_error(t('ShapeKeyApplier.error.revert.scale'), t('ShapeKeyApplier.error.revert', name=shapekey.name))
                    return {'FINISHED'}

            # TODO: Include error message.
            # Common.show_error(t('ShapeKeyApplier.error.revert.scale'), t('ShapeKeyApplier.error.revert'))
            return {'FINISHED'}

        # Set up shape keys
        obj.show_only_shape_key = False
        bpy.ops.object.shape_key_clear()

        # Create a copy of the new basis shape key to make its current value stay as it is
        new_basis_shape_key.value = new_basis_shape_key_value
        if new_basis_shape_key_value == 0:
            new_basis_shape_key.value = 1
        new_basis_shape_key.name = new_basis_shape_key_name + '--Old'

        # Replace old new basis with new new basis
        new_basis_shape_key = obj.shape_key_add(name=new_basis_shape_key_name, from_mix=True)
        new_basis_shape_key.value = 1

        # Delete the old one
        for index in reversed(range(0, len(obj.data.shape_keys.key_blocks))):
            obj.active_shape_key_index = index
            shapekey = obj.active_shape_key
            if shapekey.name == new_basis_shape_key_name + '--Old':
                bpy.ops.object.shape_key_remove(all=False)
                break

        # Find old basis and rename it
        old_basis_shape_key = obj.data.shape_keys.key_blocks[0]
        old_basis_shape_key.name = new_basis_shape_key_name + ' - Reverted'
        old_basis_shape_key.relative_key = new_basis_shape_key

        # Rename new basis after old basis was renamed
        new_basis_shape_key.name = 'Basis'

        # Mix every shape keys with the new basis
        for index in range(0, len(obj.data.shape_keys.key_blocks)):
            obj.active_shape_key_index = index
            shapekey = obj.active_shape_key
            if shapekey and shapekey.name != 'Basis' and ' - Reverted' not in shapekey.name:
                shapekey.value = 1
                obj.shape_key_add(name=shapekey.name + '-New', from_mix=True)
                shapekey.value = 0

        # Remove all the unmixed shape keys except basis and the reverted ones
        for index in reversed(range(0, len(obj.data.shape_keys.key_blocks))):
            obj.active_shape_key_index = index
            shapekey = obj.active_shape_key
            if shapekey and not shapekey.name.endswith('-New') and shapekey.name != 'Basis' and ' - Reverted' not in shapekey.name:
                bpy.ops.object.shape_key_remove(all=False)

        # Fix the names and the relative shape key
        for index, shapekey in enumerate(obj.data.shape_keys.key_blocks):
            if shapekey and shapekey.name.endswith('-New'):
                shapekey.name = shapekey.name[:-4]
                shapekey.relative_key = new_basis_shape_key

        # Repair important shape key order
        common.sort_shape_keys(obj)

        # Correctly apply the new basis as basis (important step, doesn't work otherwise)
        common.switch('EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.remove_doubles(threshold=0)
        common.switch('OBJECT')

        # If a reversed shape key was applied as basis, fix the name
        if ' - Reverted - Reverted' in old_basis_shape_key.name:
            old_basis_shape_key.name = old_basis_shape_key.name.replace(' - Reverted - Reverted', '')
            # TODO: REPORT
            pass
            # self.report({'INFO'}, t('ShapeKeyApplier.successRemoved', name=old_basis_shape_key.name))
        else:
            # TODO: REPORT
            pass
            # self.report({'INFO'}, t('ShapeKeyApplier.successSet', name=new_basis_shape_key_name))
        return {'FINISHED'}


class _SelectAffectedShapeKeyVertices(bpy.types.Operator):
    """
    Selects vertices and are affected by a shape key.
    """

    bl_label = "Select Affected Shape Key Vertices"
    bl_idname = "creaturetime.select_affected_shape_key_vertices"
    bl_description = "Selects vertices and are affected by a shape key."
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    __Tolerance = 1e-5

    @classmethod
    def poll(cls, context):
        return context.object.active_shape_key and context.object.active_shape_key_index > 0

    def execute(self, context):
        obj = bpy.context.active_object

        shape_keys = obj.data.shape_keys.key_blocks
        sk1_data = context.object.active_shape_key.data
        skb_data = shape_keys['Basis'].data

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.object.mode_set(mode="OBJECT")

        for i, (x, y) in enumerate(zip(sk1_data, skb_data)):
            if (x.co - y.co).length > _SelectAffectedShapeKeyVertices.__Tolerance:
                obj.data.vertices[i].select = True

        bpy.ops.object.mode_set(mode="EDIT")

        return {'FINISHED'}


def apply_operators(self, _):
    layout = self.layout
    layout.operator(_RemoveUnusedShapeKeys.bl_idname, icon_value=resources.get('default_white_x16').icon_id)
    layout.operator(_ApplyShapeKeyAsBasis.bl_idname, icon_value=resources.get('default_white_x16').icon_id)
    layout.operator(_SelectAffectedShapeKeyVertices.bl_idname, icon_value=resources.get('default_white_x16').icon_id)
    layout.separator()


def register():
    bpy.utils.register_class(_RemoveUnusedShapeKeys)
    bpy.utils.register_class(_ApplyShapeKeyAsBasis)
    bpy.utils.register_class(_SelectAffectedShapeKeyVertices)

    bpy.types.MESH_MT_shape_key_context_menu.prepend(apply_operators)


def unregister():
    bpy.types.MESH_MT_shape_key_context_menu.remove(apply_operators)

    bpy.utils.unregister_class(_RemoveUnusedShapeKeys)
    bpy.utils.unregister_class(_ApplyShapeKeyAsBasis)
    bpy.utils.unregister_class(_SelectAffectedShapeKeyVertices)
