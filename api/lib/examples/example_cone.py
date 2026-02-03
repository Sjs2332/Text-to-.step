"""
EXAMPLE: Cone
Prompt: "Cone with 20mm base radius, 5mm top radius, 30mm tall"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Truncated cone (frustum)
    body = utils.create_cone(
        "Cone",
        radius1=20,  # Bottom radius
        radius2=5,   # Top radius (0 for point)
        height=30,
        position=Base.Vector(0, 0, 0)
    )
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)


# Cone is useful for transitions and funnels:
def generate_funnel(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Outer cone
    outer = utils.create_cone("Outer", 40, 10, 50)
    
    # Inner cone (slightly smaller)
    inner = utils.create_cone("Inner", 38, 8, 52,
                              position=Base.Vector(0, 0, -1))
    
    # Cut to make hollow funnel
    body = utils.cut_objects(outer, inner)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
