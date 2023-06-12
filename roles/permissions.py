from flask_principal import Permission, RoleNeed
# list various permission types here

# Create a permission with a single Need, in this case a RoleNeed.
admin_permission = Permission(RoleNeed('Admin'))
view_permission = Permission(RoleNeed('View'))
add_story_permission = Permission(RoleNeed('Add Story'))

add_driver_permission = Permission(RoleNeed('Add Driver'))
edit_story_permission = Permission(RoleNeed('Edit Story'))
delete_story_permission = Permission(RoleNeed('Delete Story'))
delete_driver_permission = Permission(RoleNeed('Delete Driver'))
edit_driver_permission = Permission(RoleNeed('Edit Driver'))
