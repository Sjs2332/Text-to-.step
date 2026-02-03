"""
EXAMPLE: U-Bracket/Channel
Prompt: "U-channel bracket, 60mm wide, 40mm tall legs, 30mm deep, 
         4mm thick, 6mm holes, 2 per leg"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_u_bracket(
        "UBracket",
        width=60,
        height=40,
        depth=30,
        thickness=4,
        hole_dia=6,
        holes_per_leg=2,
        fillet_radius=2
    )
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
