"""
EXAMPLE: Pipe Flange
Prompt: "4-inch pipe flange, 150mm OD, 102mm bore, 20mm thick,
         6 x 12mm bolt holes on 125mm BCD, raised hub 115mm x 10mm"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_pipe_flange(
        "PipeFlange",
        outer_dia=150,
        inner_dia=102,
        thickness=20,
        bolt_circle_dia=125,
        bolt_hole_dia=12,
        bolt_count=6,
        hub_dia=115,
        hub_height=10
    )
    
    # Optional: chamfer on outer edge
    top_edges = utils.select_edges(body, z_level=30)  # 20 + 10 hub
    if top_edges:
        body = utils.apply_chamfer(body, 2, edge_names=top_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
