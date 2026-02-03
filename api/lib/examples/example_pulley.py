"""
EXAMPLE: V-Belt Pulley
Prompt: "Pulley for A-section V-belt, 80mm OD, 12mm bore, 20mm wide, 2 grooves"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_pulley(
        "Pulley",
        outer_dia=80,
        bore_dia=12,
        width=20,
        groove_count=2,
        groove_depth=4,
        groove_angle=40  # Standard V-belt angle
    )
    
    # Add keyway
    keyway = utils.create_box("keyway", 4, 15, 2.5, center=True,
                              position=Base.Vector(0, 0, 5))
    body = utils.cut_objects(body, keyway)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
