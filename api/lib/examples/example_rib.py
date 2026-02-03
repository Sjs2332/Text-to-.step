"""
EXAMPLE: Structural Rib
Prompt: "Reinforcement rib, 40mm long, 15mm tall, 3mm thick"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Create L-shaped base to reinforce
    base = utils.create_box("Base", 60, 40, 5, center=True)
    wall = utils.create_box("Wall", 5, 40, 30, 
                           position=Base.Vector(-30, -20, 2.5))
    body = utils.fuse_objects([base, wall])
    
    # Add reinforcement rib connecting wall to base
    rib = utils.create_rib(
        "Rib",
        length=40,
        height=15,
        thickness=3,
        position=Base.Vector(-27.5, 0, 2.5),
        direction='Y'
    )
    body = utils.fuse_objects([body, rib])
    
    # Fillet the rib edges for strength
    rib_edges = utils.select_edges(body, z_level=2.5)
    if rib_edges:
        body = utils.apply_fillet(body, 2, edge_names=rib_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
