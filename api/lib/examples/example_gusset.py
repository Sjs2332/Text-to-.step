"""
EXAMPLE: Gusset (Triangular Support)
Prompt: "Gusset 25mm wide, 20mm tall, 4mm thick"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Create L-bracket base to add gusset to
    base = utils.create_box("Base", 50, 30, 5)
    wall = utils.create_box("Wall", 5, 30, 40, 
                           position=Base.Vector(0, 0, 5))
    body = utils.fuse_objects([base, wall])
    
    # Add gusset for reinforcement
    gusset = utils.create_gusset(
        "Gusset",
        width=25,      # Along base
        height=20,     # Up the wall
        thickness=4,
        position=Base.Vector(5, 13, 5)  # At inside corner
    )
    body = utils.fuse_objects([body, gusset])
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
