"""
EXAMPLE: Countersink Hole (for flat head screws)
Prompt: "M5 countersink hole, 15mm deep, 10mm countersink dia, 90° angle"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Create a plate to cut the countersink into
    body = utils.create_box("Plate", 60, 40, 10, center=True)
    
    # Create countersink and cut it
    cs = utils.create_countersink(
        "CS_M5",
        hole_dia=5.5,      # M5 clearance
        hole_depth=15,     # Through + extra
        cs_dia=10,         # Countersink diameter
        cs_angle=90,       # Standard flat head angle
        position=Base.Vector(0, 0, 5 - 2.5)  # Near top surface
    )
    body = utils.cut_objects(body, cs)
    
    # Add a second one offset
    cs2 = utils.create_countersink(
        "CS_M5_2",
        hole_dia=5.5,
        hole_depth=15,
        cs_dia=10,
        cs_angle=90,
        position=Base.Vector(20, 0, 5 - 2.5)
    )
    body = utils.cut_objects(body, cs2)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
