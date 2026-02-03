"""
EXAMPLE: Adjustment Slot
Prompt: "Slot 25mm long, 8mm wide, 5mm deep for adjustment"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Create mounting plate
    body = utils.create_box("Plate", 80, 40, 8, center=True)
    
    # Create adjustment slot (rounded ends)
    slot = utils.create_slot(
        "AdjustSlot",
        length=25,
        width=8,
        depth=10,  # Through plate
        position=Base.Vector(0, 0, 0)
    )
    body = utils.cut_objects(body, slot)
    
    # Add fixed mounting holes on each side
    hole1 = utils.create_hole("Hole1", 6, 10, position=Base.Vector(-30, 0, 0))
    hole2 = utils.create_hole("Hole2", 6, 10, position=Base.Vector(30, 0, 0))
    body = utils.cut_objects(body, hole1)
    body = utils.cut_objects(body, hole2)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
