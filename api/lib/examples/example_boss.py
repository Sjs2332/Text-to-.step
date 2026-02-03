"""
EXAMPLE: Mounting Boss
Prompt: "Boss 10mm OD, 8mm tall, 4mm screw hole"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Create base plate
    body = utils.create_box("Base", 50, 50, 3, center=True)
    
    # Add single boss with screw hole
    boss = utils.create_boss(
        "MountBoss",
        outer_dia=10,
        height=8,
        hole_dia=4,  # For self-tapping screw
        position=Base.Vector(0, 0, 1.5)  # On top of plate
    )
    body = utils.fuse_objects([body, boss])
    
    # Add fillet at boss base
    base_edges = utils.select_edges(body, edge_type='Circle', z_level=1.5)
    if base_edges:
        body = utils.apply_fillet(body, 1.5, edge_names=base_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)


# For multiple bosses in a pattern, see example_enclosure.py
# which uses add_enclosure_bosses() mega-function
