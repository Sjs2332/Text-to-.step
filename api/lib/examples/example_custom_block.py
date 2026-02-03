"""
EXAMPLE: Custom Part with Multiple Features
Prompt: "Aluminum block 80x50x20mm with:
         - 4 x M5 counterbore holes at corners (15mm from edges)
         - Central 25mm pocket (10mm deep, R3 corners)
         - 10mm slot on side for adjustment"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    L, W, H = 80, 50, 20
    
    # 1. Base block
    body = utils.create_box("Block", L, W, H, center=True)
    
    # 2. Counterbore holes at corners (15mm from edge = 25mm from center)
    cb_positions = [
        (-L/2 + 15, -W/2 + 15),
        ( L/2 - 15, -W/2 + 15),
        (-L/2 + 15,  W/2 - 15),
        ( L/2 - 15,  W/2 - 15),
    ]
    
    for i, (x, y) in enumerate(cb_positions):
        cb = utils.create_counterbore(
            f"CB_{i}",
            hole_dia=5.5,      # M5 clearance
            hole_depth=H + 1,
            cb_dia=10,         # Socket head
            cb_depth=5,
            position=Base.Vector(x, y, H/2 - 5)
        )
        body = utils.cut_objects(body, cb)
    
    # 3. Central pocket
    pocket = utils.create_pocket("CenterPocket", 25, 25, 10, corner_radius=3,
                                 position=Base.Vector(0, 0, H/2 - 10))
    body = utils.cut_objects(body, pocket)
    
    # 4. Side slot
    slot = utils.create_slot("AdjustSlot", 20, 6, W + 1,
                            position=Base.Vector(L/2 - 10, 0, H/2 - 3))
    slot = utils.rotate_object(slot, Base.Vector(1, 0, 0), 90)
    body = utils.cut_objects(body, slot)
    
    # 5. Chamfer all top edges
    top_edges = utils.select_edges(body, z_level=H/2)
    if top_edges:
        body = utils.apply_chamfer(body, 1, edge_names=top_edges)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
