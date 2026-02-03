"""
EXAMPLE: Flanged Bushing
Prompt: "Bushing, 20mm OD, 12mm ID, 25mm long, with 30mm flange (3mm thick)"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_bushing(
        "Bushing",
        outer_dia=20,
        inner_dia=12,
        length=25,
        flange_dia=30,
        flange_thickness=3
    )
    
    # Chamfer bore ends
    bore_edges = utils.select_edges(body, edge_type='Circle', min_radius=5, max_radius=7)
    if bore_edges:
        body = utils.apply_chamfer(body, 0.5, edge_names=bore_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
