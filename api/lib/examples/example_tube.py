"""
EXAMPLE: Tube/Pipe Section
Prompt: "Pipe section, 50mm OD, 40mm ID, 100mm long"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_tube(
        "Pipe",
        outer_dia=50,
        inner_dia=40,
        length=100
    )
    
    # Optional: chamfer ends
    end_edges = utils.select_edges(body, edge_type='Circle')
    if end_edges:
        body = utils.apply_chamfer(body, 1, edge_names=end_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
