"""
EXAMPLE: Spur Gear
Prompt: "Spur gear, module 2, 24 teeth, 10mm thick, 8mm bore,
         hub 20mm dia x 5mm"
"""
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_spur_gear(
        "SpurGear",
        module=2,
        teeth=24,
        thickness=10,
        bore_dia=8,
        hub_dia=20,
        hub_height=5
    )
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)


# NOTE: For production gears, consider:
# - pitch_diameter = module * teeth = 48mm
# - outer_diameter = pitch_dia + 2*module = 52mm
# - root_diameter = pitch_dia - 2.5*module = 43mm
