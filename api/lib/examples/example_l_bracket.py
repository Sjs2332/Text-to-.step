"""
EXAMPLE: L-Bracket with mounting holes
Prompt: "L-bracket, 50mm vertical leg, 40mm horizontal leg, 25mm wide, 
         3mm thick, 5mm holes at leg centers, R3 inside fillet"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Use mega-function
    body = utils.create_l_bracket(
        "LBracket",
        leg1_length=50,      # Vertical leg
        leg2_length=40,      # Horizontal leg
        width=25,
        thickness=3,
        hole_dia=5,
        hole_positions=[(1, 25), (2, 20)],  # (leg, offset from corner)
        fillet_radius=3
    )
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
