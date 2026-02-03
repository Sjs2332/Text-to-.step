"""
EXAMPLE: Flat Mounting Bracket
Prompt: "Flat bracket, 100mm long, 20mm wide, 3mm thick, 4 x 6mm holes"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_flat_bracket(
        "FlatBracket",
        length=100,
        width=20,
        thickness=3,
        hole_dia=6,
        hole_count=4
    )
    
    # Optional: round the ends
    end_edges = utils.select_edges(body, direction='Z')
    if end_edges:
        body = utils.apply_fillet(body, 10, edge_names=end_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
