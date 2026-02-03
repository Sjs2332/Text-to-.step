"""
EXAMPLE: Rectangular Pocket
Prompt: "Pocket 30x20mm, 8mm deep, R3 corners"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Create block
    body = utils.create_box("Block", 60, 40, 15, center=True)
    
    # Create pocket with rounded corners
    pocket = utils.create_pocket(
        "Pocket",
        length=30,
        width=20,
        depth=8,
        corner_radius=3,
        position=Base.Vector(0, 0, 7.5 - 8)  # From top
    )
    body = utils.cut_objects(body, pocket)
    
    # Add mounting holes in corners
    for x, y in [(-22, -12), (22, -12), (-22, 12), (22, 12)]:
        hole = utils.create_hole(f"Hole_{x}_{y}", 5, 20,
                                 position=Base.Vector(x, y, 0))
        body = utils.cut_objects(body, hole)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
