"""
EXAMPLE: Counterbore Hole (for socket head cap screws)
Prompt: "M6 counterbore hole, 20mm deep, 11mm counterbore dia, 6mm deep"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Create a block to cut the counterbore into
    body = utils.create_box("Block", 50, 50, 25, center=True)
    
    # Create counterbore and cut it
    cb = utils.create_counterbore(
        "CB_M6",
        hole_dia=6.5,      # M6 clearance
        hole_depth=30,     # Through + extra
        cb_dia=11,         # Socket head diameter
        cb_depth=6,        # Head height
        position=Base.Vector(0, 0, 12.5 - 6)  # From top surface
    )
    body = utils.cut_objects(body, cb)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
