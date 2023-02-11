#----------------------------------------------------------
# File __init__.py
#----------------------------------------------------------
 
#    Addon info
bl_info = {
    "name": "Autogrip",
    "author": "Jetpack Crow",
    "version": (1, 21),
    "blender": (3, 4, 1),
    "location": "View3D > Extended Tools > AutoGrip",
    "description": "Automatically poses hand rigs",
    "category": '3D View'}
if "bpy" in locals():
    import imp
    imp.reload(handrig)
    print("Reloaded Autogrip")
else:
    from . import handrig
    print("Imported Autogrip") 


def register():
    handrig.register()

    
def unregister():
    handrig.unregister()

    
if __name__ == "__main__":
    register()
