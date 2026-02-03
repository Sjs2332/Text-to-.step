"""
EXAMPLE: Torus (Donut/O-Ring shape)
Prompt: "Torus with 30mm major radius, 5mm minor radius"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Simple torus
    body = utils.create_torus(
        "Torus",
        radius1=30,  # Major radius (center to tube center)
        radius2=5,   # Minor radius (tube radius)
        position=Base.Vector(0, 0, 0)
    )
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)


# Torus is also useful for O-ring grooves:
def generate_oring_groove(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Shaft with O-ring groove
    shaft = utils.create_cylinder("Shaft", 15, 50, center=True)
    
    # Cut O-ring groove using torus
    groove = utils.create_torus("Groove", 15, 2,  # At shaft surface
                                position=Base.Vector(0, 0, 0))
    shaft = utils.cut_objects(shaft, groove)
    
    utils.export_step(shaft, step_path)
    utils.export_stl(shaft, stl_path)
