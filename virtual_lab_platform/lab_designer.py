"""Configurable virtual-lab workbench with explicit validation levels.

The catalog is illustrative and intentionally separates inventory metadata from
scientific simulation. Only workflows with a declared calculator are executed.
"""
from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Any
from models import execute_model

ENGINE_ID = "lab_workflow_designer"
ENGINE_VERSION = "1.0"

CATALOG: dict[str, Any] = {
    "disciplines": [
        {"id": "biology", "name": "Biology & biochemistry"},
        {"id": "chemistry", "name": "Chemistry"},
        {"id": "medicine", "name": "Biomedical research"},
        {"id": "physics", "name": "Physics & materials"},
        {"id": "environment", "name": "Environmental science"},
        {"id": "engineering", "name": "Engineering"},
    ],
    "components": [
        {"id":"water","name":"Purified water","category":"solvent","disciplines":["biology","chemistry"],"unit":"mL","hazards":[],"description":"Generic diluent for calculation demos."},
        {"id":"buffer","name":"Buffer solution (generic)","category":"solution","disciplines":["biology","chemistry"],"unit":"mL","hazards":[],"description":"Placeholder; buffer composition and pH are not modeled."},
        {"id":"substrate","name":"Enzyme substrate (generic)","category":"reagent","disciplines":["biology","chemistry"],"unit":"mL","hazards":[],"description":"Generic model input; no real chemical identity or safety data."},
        {"id":"enzyme","name":"Enzyme sample (generic)","category":"biological reagent","disciplines":["biology","medicine"],"unit":"mL","hazards":["biological_material"],"description":"Abstract enzyme variable for the Michaelis–Menten demo."},
        {"id":"cell_sample","name":"Cell sample (placeholder)","category":"biological sample","disciplines":["biology","medicine"],"unit":"sample","hazards":["biological_material"],"description":"Workflow placeholder only; no cell biology simulator attached."},
        {"id":"dna_sample","name":"DNA sample (placeholder)","category":"biological sample","disciplines":["biology","medicine"],"unit":"sample","hazards":["biological_material"],"description":"Workflow placeholder only; no sequence or PCR model attached."},
        {"id":"salt","name":"Sodium chloride (generic)","category":"reagent","disciplines":["chemistry","biology"],"unit":"g","hazards":[],"description":"No solubility, activity or ionic-strength model attached."},
        {"id":"polymer","name":"Polymer sample (placeholder)","category":"material","disciplines":["chemistry","physics","engineering"],"unit":"g","hazards":[],"description":"Material placeholder; no constitutive material model attached."},
        {"id":"environmental_sample","name":"Environmental sample (placeholder)","category":"sample","disciplines":["environment"],"unit":"sample","hazards":["unknown_sample"],"description":"Unknown composition; no contaminant analysis model attached."},
        {"id":"population_model","name":"Population model inputs (abstract) ","category":"model input","disciplines":["medicine","environment"],"unit":"configuration","hazards":[],"description":"Abstract model configuration; no individual or local outbreak prediction."},
    ],
    "equipment": [
        {"id":"pipette","name":"Adjustable pipette (up to 1 mL)","category":"liquid handling","disciplines":["biology","chemistry","medicine"],"capabilities":["measure_volume","transfer_liquid"],"max_volume_ml":1.0,"transfer_uncertainty_sd_ml":0.006,"measurement_uncertainty_sd":0.01,"measurement_unit":"mL","precision_note":"Illustrative 1 mL capacity; illustrative one-sigma transfer uncertainty 0.006 mL; not a certified specification."},
        {"id":"pipette_10ml","name":"Serological pipette (up to 10 mL)","category":"liquid handling","disciplines":["biology","chemistry","medicine"],"capabilities":["measure_volume","transfer_liquid"],"max_volume_ml":10.0,"transfer_uncertainty_sd_ml":0.05,"measurement_uncertainty_sd":0.05,"measurement_unit":"mL","precision_note":"Illustrative 10 mL capacity; illustrative one-sigma transfer uncertainty 0.05 mL; not a certified specification."},
        {"id":"beaker","name":"Laboratory beaker","category":"glassware","disciplines":["biology","chemistry","physics"],"capabilities":["hold_liquid","mix"],"max_volume_ml":250.0,"precision_note":"Not a precision volumetric instrument."},
        {"id":"spectrophotometer","name":"Spectrophotometer","category":"measurement","disciplines":["biology","chemistry","medicine"],"capabilities":["measure_absorbance"],"max_volume_ml":3.0,"measurement_uncertainty_sd":0.005,"measurement_unit":"AU","precision_note":"Illustrative one-sigma read uncertainty 0.005 AU; wavelength/path-length response is not modeled."},
        {"id":"incubator","name":"Temperature-controlled incubator","category":"temperature control","disciplines":["biology","medicine"],"capabilities":["control_temperature"],"temperature_min_c":4,"temperature_max_c":80,"temperature_control_uncertainty_sd_c":0.5,"precision_note":"Illustrative range only; no heat-transfer dynamics model attached."},
        {"id":"centrifuge","name":"Laboratory centrifuge","category":"separation","disciplines":["biology","medicine","chemistry"],"capabilities":["centrifuge"],"max_rpm":15000,"precision_note":"No rotor, radius, RCF or sample-balance model attached."},
        {"id":"microscope","name":"Optical microscope","category":"imaging","disciplines":["biology","medicine","environment"],"capabilities":["image_sample"],"precision_note":"No image formation or optical simulation attached."},
        {"id":"ph_meter","name":"pH meter","category":"measurement","disciplines":["biology","chemistry","environment"],"capabilities":["measure_ph"],"measurement_uncertainty_sd":0.02,"measurement_unit":"pH","precision_note":"Illustrative one-sigma read uncertainty 0.02 pH; acid-base chemistry is not modeled."},
        {"id":"thermal_cycler","name":"Thermal cycler (PCR instrument)","category":"temperature control","disciplines":["biology","medicine"],"capabilities":["temperature_program"],"precision_note":"PCR is currently a workflow template only; no amplification model attached."},
        {"id":"analytical_balance","name":"Analytical balance","category":"measurement","disciplines":["chemistry","engineering"],"capabilities":["measure_mass"],"max_mass_g":220,"measurement_uncertainty_sd":0.001,"measurement_unit":"g","precision_note":"Illustrative one-sigma read uncertainty 0.001 g; not a certified specification."},
        {"id":"thermal_chamber","name":"Thermal chamber","category":"temperature control","disciplines":["physics","engineering"],"capabilities":["control_temperature"],"temperature_min_c":-40,"temperature_max_c":250,"temperature_control_uncertainty_sd_c":1.0,"precision_note":"No chamber control dynamics or thermal uniformity model attached."},
        {"id":"thermometer","name":"Digital laboratory thermometer","category":"measurement","disciplines":["biology","chemistry","physics","environment","engineering"],"capabilities":["measure_temperature"],"measurement_uncertainty_sd":0.5,"measurement_unit":"°C","precision_note":"Illustrative one-sigma read uncertainty 0.5 °C; calibration and response time are not modeled."},
        {"id":"fume_hood","name":"Chemical fume hood","category":"safety equipment","disciplines":["chemistry"],"capabilities":["contain_vapours"],"precision_note":"Inventory/safety reminder only; does not certify risk controls."},
        {"id":"simulation_workstation","name":"Numerical simulation workstation (abstract)","category":"computing","disciplines":["medicine","environment","physics","engineering"],"capabilities":["execute_numerical_model"],"precision_note":"Software resource placeholder; does not represent a certified hardware device."},
    ],
    "workflows": [
        {"id":"solution_dilution","name":"Solution dilution calculator","discipline":"chemistry","simulation_level":"L1","required_components":["water"],"required_equipment":["beaker"],"required_equipment_options":[["pipette","pipette_10ml"]],"description":"Computes C1×V1/Vfinal for an ideal dilution. Does not model chemistry, heat, non-ideal mixing or real instrument error."},
        {"id":"enzyme_assay","name":"Enzyme assay (Michaelis–Menten demo)","discipline":"biology","simulation_level":"L1","required_components":["substrate","enzyme"],"required_equipment":["pipette","spectrophotometer","incubator"],"description":"Computes an illustrative Michaelis–Menten curve. Equipment is checked for availability; measurement physics and biological validation are not simulated."},
        {"id":"microscopy","name":"Microscopy workflow","discipline":"biology","simulation_level":"L0","required_components":["cell_sample"],"required_equipment":["microscope"],"description":"Protocol can be assembled and checked, but no image or biological outcome is calculated."},
        {"id":"pcr_workflow","name":"PCR workflow template","discipline":"biology","simulation_level":"L0","required_components":["dna_sample"],"required_equipment":["pipette","thermal_cycler"],"description":"Workflow template only. No amplification, primer specificity, contamination or yield model is connected."},
        {"id":"environmental_screening","name":"Environmental sample screening","discipline":"environment","simulation_level":"L0","required_components":["environmental_sample"],"required_equipment":["ph_meter"],"description":"Workflow template only. No contaminant or environmental-risk result is calculated."},
        {"id":"materials_heating","name":"1D material heat diffusion simulation","discipline":"physics","simulation_level":"L1","required_components":["polymer"],"required_equipment":["thermal_chamber"],"description":"Runs the existing explicit 1D heat diffusion solver for a homogeneous bar with fixed boundary temperatures. No phase change, convection or material heterogeneity."},
        {"id":"epidemic_sir","name":"SIR population dynamics simulation","discipline":"medicine","simulation_level":"L1","required_components":["population_model"],"required_equipment":["simulation_workstation"],"description":"Runs a simple susceptible–infectious–recovered compartment model. Educational, not for outbreak decisions or individual predictions."},
    ]
}

# Expanded multidisciplinary inventory. These entries improve discoverability and
# experiment planning; L0 workflows remain templates unless a solver is explicitly connected.
CATALOG["disciplines"].extend([
    {"id":"materials","name":"Materials science"},
    {"id":"electronics","name":"Electronics & circuits"},
    {"id":"geoscience","name":"Geosciences"},
    {"id":"astronomy","name":"Astronomy & space science"},
    {"id":"fluid_mechanics","name":"Fluid mechanics"},
    {"id":"agriculture","name":"Agriculture & plant science"},
    {"id":"genetics","name":"Genetics & molecular biology"},
    {"id":"neuroscience","name":"Neuroscience"},
    {"id":"data_science","name":"Scientific data science"},
    {"id":"microbiology","name":"Microbiology"},
    {"id":"food_science","name":"Food science"},
    {"id":"energy","name":"Energy systems"},
])

_EXTRA_COMPONENTS = [
("ethanol_sample","Ethanol (identity placeholder)","solvent",["chemistry","food_science"],"mL",["flammable"],"Inventory placeholder only; concentration, purity and safety data are not supplied."),
("glucose_solution","Glucose solution (generic)","solution",["biology","chemistry","food_science"],"mL",[],"Generic solution; no concentration is implied."),
("acid_solution","Acid solution (unspecified)","reagent",["chemistry"],"mL",["corrosive_unknown"],"Unspecified acid: no handling recommendation or reaction prediction."),
("base_solution","Base solution (unspecified)","reagent",["chemistry"],"mL",["corrosive_unknown"],"Unspecified base: no handling recommendation or reaction prediction."),
("indicator_solution","pH indicator solution (generic)","reagent",["chemistry"],"mL",["unknown_composition"],"Visual indicator placeholder; no colour-transition model."),
("catalyst_sample","Catalyst sample (generic)","material",["chemistry","engineering"],"g",[],"No catalyst identity, surface area or catalytic mechanism is modeled."),
("metal_sample","Metal sample (generic)","material",["chemistry","physics","materials","engineering"],"g",[],"No alloy composition or material properties are implied."),
("ceramic_sample","Ceramic sample (generic)","material",["physics","materials","engineering"],"sample",[],"Placeholder; no fracture, thermal or constitutive model."),
("composite_sample","Composite sample (generic)","material",["materials","engineering"],"sample",[],"No fibre orientation, matrix properties or failure model."),
("soil_sample","Soil sample (unknown)","sample",["environment","geoscience","agriculture"],"sample",["unknown_sample"],"Composition and contamination are unknown; no site-specific result."),
("water_sample","Water sample (unknown)","sample",["environment","chemistry","geoscience"],"sample",["unknown_sample"],"No contaminant concentration or potability assessment is calculated."),
("air_sample","Air sample (unknown)","sample",["environment","engineering"],"sample",["unknown_sample"],"No gas composition or exposure assessment is calculated."),
("plant_sample","Plant tissue sample (placeholder)","biological sample",["biology","agriculture","genetics"],"sample",["biological_material"],"No species, genotype or plant-health outcome is implied."),
("microbial_sample","Microbial sample (placeholder)","biological sample",["microbiology","biology","food_science"],"sample",["biological_material"],"No organism identification, growth or biosafety classification is provided."),
("protein_sample","Protein sample (placeholder)","biological sample",["biology","genetics","medicine"],"sample",["biological_material"],"No sequence, structure or activity model is attached."),
("rna_sample","RNA sample (placeholder)","biological sample",["genetics","biology","medicine"],"sample",["biological_material"],"No sequence or gene-expression result is calculated."),
("lipid_sample","Lipid sample (generic)","reagent",["biology","chemistry","food_science"],"g",[],"Generic material; no composition or phase-behaviour model."),
("buffer_phosphate","Phosphate buffer (placeholder)","solution",["biology","chemistry"],"mL",[],"Buffer concentration and pH are unspecified; no buffer-capacity calculation."),
("nutrient_solution","Plant nutrient solution (generic)","solution",["agriculture","biology"],"mL",[],"No nutrient recipe, crop-specific dose or agronomic recommendation."),
("fertilizer_sample","Fertilizer sample (unspecified)","material",["agriculture","environment"],"g",["unknown_composition"],"No formulation, nutrient analysis or environmental risk assessment."),
("food_sample","Food sample (placeholder)","sample",["food_science","microbiology","chemistry"],"sample",["unknown_sample"],"No nutritional, allergen, pathogen or shelf-life result."),
("battery_cell","Battery cell (abstract)","electrical component",["electronics","energy","engineering"],"unit",[],"No chemistry-specific battery degradation or safety model."),
("resistor_component","Resistor (abstract)","electrical component",["electronics","physics","engineering"],"unit",[],"Ideal resistance only when connected to the circuit solver."),
("capacitor_component","Capacitor (abstract)","electrical component",["electronics","physics","engineering"],"unit",[],"Inventory placeholder; only supported circuit models can calculate its response."),
("inductor_component","Inductor (abstract)","electrical component",["electronics","physics","engineering"],"unit",[],"Inventory placeholder; parasitic effects are not implied."),
("solar_cell","Solar cell (abstract)","energy component",["energy","electronics","physics"],"unit",[],"No photovoltaic I–V curve or irradiance response is attached."),
("fuel_sample","Fuel sample (unspecified)","energy material",["energy","chemistry","engineering"],"mL",["flammable_unknown"],"No fuel identity, combustion or safety result is calculated."),
("rock_sample","Rock sample (unknown)","geological sample",["geoscience","environment"],"sample",["unknown_sample"],"No mineral identification or geological age analysis."),
("mineral_sample","Mineral sample (unknown)","geological sample",["geoscience","materials"],"sample",["unknown_sample"],"No composition, hardness or crystal structure is identified."),
("sediment_sample","Sediment sample (unknown)","geological sample",["geoscience","environment"],"sample",["unknown_sample"],"No particle-size, transport or contaminant model."),
("meteorite_sample","Meteorite sample (placeholder)","astronomy sample",["astronomy","geoscience","materials"],"sample",["unknown_sample"],"Placeholder only; no origin or composition is inferred."),
("cell_culture_medium","Cell culture medium (generic)","solution",["biology","medicine","microbiology"],"mL",["biological_context"],"No cell-line-specific composition, sterility or growth prediction."),
("antibody_sample","Antibody sample (placeholder)","biological reagent",["biology","medicine"],"sample",["biological_material"],"No binding affinity or immunoassay result is calculated."),
("enzyme_inhibitor","Enzyme inhibitor (generic)","reagent",["biology","chemistry"],"g",[],"No target specificity, potency or toxicity model."),
("polymer_solution","Polymer solution (generic)","solution",["materials","chemistry","engineering"],"mL",[],"No molecular-weight distribution or rheology model."),
("nanoparticle_sample","Nanoparticle sample (placeholder)","material",["materials","chemistry","medicine"],"sample",["unknown_sample"],"No size distribution, surface chemistry or exposure assessment."),
("lubricant_sample","Lubricant (generic)","material",["engineering","fluid_mechanics"],"mL",[],"No viscosity-temperature curve or tribology model."),
("gas_sample","Gas sample (unspecified)","sample",["chemistry","physics","environment"],"L",["unknown_composition"],"No species composition, pressure or hazard assessment."),
("salt_solution","Salt solution (generic)","solution",["chemistry","environment"],"mL",[],"No salt identity, concentration or activity model."),
("reference_standard","Reference standard (placeholder)","quality-control material",["chemistry","food_science","environment"],"sample",[],"No certified value or traceability is implied."),
("blank_sample","Analytical blank (placeholder)","quality-control material",["chemistry","biology","environment"],"sample",[],"Used as a workflow concept; no instrument-specific blank correction."),
("calibration_sample","Calibration sample (placeholder)","quality-control material",["chemistry","biology","environment"],"sample",[],"No certified concentration or calibration traceability is implied."),
("electrolyte_solution","Electrolyte solution (generic)","solution",["chemistry","electronics","energy"],"mL",[],"No ionic conductivity or electrochemical kinetics model."),
("coolant_sample","Coolant (generic)","thermal material",["engineering","energy","physics"],"mL",[],"No coolant chemistry or certified thermal properties."),
("water_ice_sample","Water/ice phase sample (placeholder)","phase sample",["physics","environment","geoscience"],"sample",[],"No phase-equilibrium or latent-heat model is attached."),
("dust_sample","Particulate matter sample (unknown)","environmental sample",["environment","fluid_mechanics"],"sample",["unknown_sample"],"No particle size, composition or exposure result."),
("algae_sample","Algae sample (placeholder)","biological sample",["biology","environment","agriculture"],"sample",["biological_material"],"No species, growth or carbon-uptake model."),
("seed_sample","Seed sample (placeholder)","biological sample",["agriculture","biology"],"sample",["biological_material"],"No viability or germination prediction."),
]
for _id,_name,_cat,_disc,_unit,_haz,_desc in _EXTRA_COMPONENTS:
    CATALOG["components"].append({"id":_id,"name":_name,"category":_cat,"disciplines":_disc,"unit":_unit,"hazards":_haz,"description":_desc})

_EXTRA_EQUIPMENT = [
("volumetric_flask","Volumetric flask","glassware",["chemistry","biology"],["prepare_solution"],"No calibration certificate or tolerance is implied."),
("graduated_cylinder","Graduated cylinder","glassware",["chemistry","biology","environment"],["measure_volume"],"Not a substitute for calibrated volumetric glassware."),
("burette","Burette","liquid handling",["chemistry"],["dispense_precisely"],"No certified tolerance or titration endpoint detection."),
("magnetic_stirrer","Magnetic stirrer","mixing",["chemistry","biology"],["mix"],"Mixing speed and homogeneity are not simulated."),
("hotplate_stirrer","Hotplate stirrer","heating",["chemistry","biology"],["heat","mix"],"No thermal gradients, surface temperature or feedback model."),
("water_bath","Laboratory water bath","temperature control",["biology","chemistry"],["control_temperature"],"Setpoint is an inventory property; transient heat transfer is not modeled."),
("refrigerator","Laboratory refrigerator","storage",["biology","chemistry","medicine"],["store_cold"],"No temperature excursion or sample stability model."),
("freezer","Laboratory freezer","storage",["biology","medicine"],["store_frozen"],"No freezing kinetics or sample degradation model."),
("ultra_low_freezer","Ultra-low temperature freezer","storage",["biology","medicine"],["store_ultra_cold"],"Inventory reminder only; no sample stability prediction."),
("biosafety_cabinet","Biological safety cabinet","containment",["biology","medicine","microbiology"],["contain_biological_material"],"Presence does not establish biosafety compliance or safe operating conditions."),
("autoclave","Autoclave","sterilization",["biology","medicine","microbiology"],["sterilize"],"No validated sterilization cycle or biological indicator model."),
("vacuum_pump","Vacuum pump","pressure control",["chemistry","physics","engineering"],["reduce_pressure"],"No pump curve, leak model or absolute pressure calibration."),
("pressure_vessel","Pressure vessel (abstract)","pressure equipment",["chemistry","engineering","energy"],["contain_pressure"],"Not a design or pressure-safety certification tool."),
("rotary_evaporator","Rotary evaporator","separation",["chemistry"],["evaporate_solvent"],"No vapour-liquid equilibrium or solvent-specific safety model."),
("distillation_column","Distillation column (abstract)","separation",["chemistry","engineering"],["separate_mixture"],"No tray efficiency, phase equilibrium or mixture database."),
("chromatography_system","Chromatography system (abstract)","separation",["chemistry","biology","food_science"],["separate_analytes"],"No retention, peak-shape or detector-response model."),
("electrophoresis_unit","Electrophoresis unit","separation",["biology","genetics","medicine"],["separate_biomolecules"],"No gel migration or sequence-size prediction."),
("gel_documentation_system","Gel documentation system","imaging",["biology","genetics","medicine"],["image_gel"],"No image sensor or band-quantification model."),
("plate_reader","Microplate reader","measurement",["biology","medicine","food_science"],["measure_plate_signal"],"No wavelength, path-length or assay-specific calibration."),
("fluorimeter","Fluorimeter","measurement",["chemistry","biology"],["measure_fluorescence"],"No fluorophore, quenching or detector model."),
("mass_spectrometer","Mass spectrometer (abstract)","measurement",["chemistry","biology","medicine"],["measure_mass_spectrum"],"No ionization, fragmentation or spectral library."),
("chromatography_gc","Gas chromatograph (abstract)","measurement",["chemistry","environment","food_science"],["measure_gc"],"No retention library or detector response."),
("chromatography_lc","Liquid chromatograph (abstract)","measurement",["chemistry","biology","food_science"],["measure_lc"],"No column chemistry or chromatographic simulation."),
("conductivity_meter","Conductivity meter","measurement",["chemistry","environment"],["measure_conductivity"],"No temperature compensation or ionic composition model."),
("dissolved_oxygen_meter","Dissolved oxygen meter","measurement",["environment","biology","food_science"],["measure_dissolved_oxygen"],"No sensor calibration or gas-liquid transfer model."),
("turbidity_meter","Turbidity meter","measurement",["environment","food_science"],["measure_turbidity"],"No particle optical model."),
("flow_meter","Flow meter","measurement",["fluid_mechanics","engineering","environment"],["measure_flow"],"No flow regime or instrument calibration model."),
("pressure_sensor","Pressure sensor","measurement",["physics","engineering","energy"],["measure_pressure"],"No sensor dynamics or calibration model."),
("force_sensor","Force sensor","measurement",["physics","materials","engineering"],["measure_force"],"No load-cell calibration or mechanical test model."),
("tensile_tester","Universal testing machine","mechanical testing",["materials","engineering"],["test_tensile_strength"],"No constitutive material law or certified test method."),
("hardness_tester","Hardness tester","mechanical testing",["materials","engineering"],["measure_hardness"],"No conversion between hardness scales is implied."),
("oscilloscope","Digital oscilloscope (abstract)","electronics",["electronics","physics","engineering"],["measure_voltage_waveform"],"No bandwidth, sampling or probe-loading model."),
("function_generator","Function generator (abstract)","electronics",["electronics","physics","engineering"],["generate_signal"],"No output impedance or distortion model."),
("dc_power_supply","DC bench power supply","electronics",["electronics","physics","engineering"],["supply_dc"],"Ideal source only in supported circuit calculations."),
("multimeter","Digital multimeter (abstract)","measurement",["electronics","physics","engineering"],["measure_voltage_current_resistance"],"No input impedance, burden voltage or calibration model."),
("breadboard","Solderless breadboard","electronics",["electronics","engineering"],["prototype_circuit"],"Wiring layout only; parasitics and contact faults are not modeled."),
("soldering_station","Soldering station","electronics",["electronics","engineering"],["solder"],"Inventory placeholder; no thermal or occupational safety model."),
("solar_simulator","Solar simulator (abstract)","energy",["energy","physics","electronics"],["illuminate_solar_cell"],"No spectral irradiance calibration."),
("weather_station","Weather station (abstract)","environmental measurement",["environment","agriculture","geoscience"],["measure_weather"],"No sensor calibration or forecast model."),
("soil_moisture_sensor","Soil moisture sensor","environmental measurement",["agriculture","environment"],["measure_soil_moisture"],"No soil-specific calibration curve."),
("greenhouse_chamber","Plant growth chamber","environmental control",["agriculture","biology"],["control_growth_environment"],"No crop growth model or controlled-environment validation."),
("growth_chamber","Microbial/plant growth chamber","environmental control",["biology","microbiology","agriculture"],["control_growth_environment"],"No organism-specific growth prediction."),
("incubated_shaker","Incubated orbital shaker","mixing",["biology","microbiology","chemistry"],["mix","control_temperature"],"No oxygen-transfer or shear model."),
("microfluidic_chip","Microfluidic chip (abstract)","microfluidics",["biology","chemistry","engineering"],["microfluidic_flow"],"No channel-level CFD or adsorption model."),
("3d_printer","3D printer (abstract)","fabrication",["materials","engineering"],["fabricate_part"],"No printability, anisotropy or process simulation."),
("xray_diffractometer","X-ray diffractometer (abstract)","materials analysis",["materials","geoscience","physics"],["measure_xrd"],"No diffraction pattern or phase identification model."),
("thermal_analyzer","Thermal analysis instrument (abstract)","materials analysis",["materials","chemistry","physics"],["measure_thermal_transition"],"No DSC/TGA material-specific response model."),
("centrifugal_pump","Centrifugal pump (abstract)","fluid mechanics",["fluid_mechanics","engineering","energy"],["pump_fluid"],"No pump curve or cavitation model."),
("wind_tunnel","Wind tunnel (abstract)","fluid mechanics",["fluid_mechanics","engineering","physics"],["test_aerodynamics"],"No CFD or turbulence closure is attached."),
("flow_reactor","Continuous-flow reactor (abstract)","chemical engineering",["chemistry","engineering"],["continuous_reaction"],"No residence-time distribution or reactor kinetics integration."),
("solar_telescope","Solar telescope (abstract)","astronomy",["astronomy","physics"],["observe_sun"],"No optical or solar-safety model; inventory placeholder only."),
("spectrometer_optical","Optical spectrometer (abstract)","measurement",["physics","astronomy","chemistry"],["measure_spectrum"],"No optical transfer function or spectral library."),
("radiation_detector","Radiation detector (abstract)","measurement",["physics","geoscience"],["measure_radiation"],"No detector efficiency or radiation safety model."),
("seismometer","Seismometer (abstract)","geoscience",["geoscience","physics"],["measure_ground_motion"],"No instrument response or seismic inversion model."),
("gps_receiver","GNSS/GPS receiver (abstract)","measurement",["geoscience","engineering"],["measure_position"],"No positioning error or atmospheric correction model."),
("spectral_camera","Multispectral camera (abstract)","imaging",["agriculture","environment","geoscience"],["capture_spectral_image"],"No spectral calibration or classification model."),
]
for _id,_name,_cat,_disc,_caps,_note in _EXTRA_EQUIPMENT:
    CATALOG["equipment"].append({"id":_id,"name":_name,"category":_cat,"disciplines":_disc,"capabilities":_caps,"precision_note":_note})

_EXTRA_WORKFLOWS = [
("titration_template","Acid–base titration planning","chemistry",["acid_solution","base_solution"],["burette","ph_meter"],"L0","Planning template only; no acid-base equilibrium or endpoint solver."),
("spectroscopy_template","UV–Vis spectroscopy planning","chemistry",["reference_standard","blank_sample"],["spectrophotometer"],"L0","No spectrum, absorbance or calibration curve is calculated by this workflow."),
("fluorescence_template","Fluorescence assay planning","biology",["protein_sample","blank_sample"],["fluorimeter"],"L0","No fluorophore response or quenching model is connected."),
("chromatography_template","Chromatography method planning","chemistry",["reference_standard"],["chromatography_system"],"L0","No retention, resolution or chromatogram simulation."),
("mass_spectrometry_template","Mass spectrometry planning","chemistry",["reference_standard"],["mass_spectrometer"],"L0","No spectrum interpretation or identification result."),
("protein_separation_template","Protein gel electrophoresis planning","genetics",["protein_sample"],["electrophoresis_unit","gel_documentation_system"],"L0","No migration or band-intensity model."),
("rna_expression_template","Gene expression study planning","genetics",["rna_sample"],["thermal_cycler","plate_reader"],"L0","No assay design, expression calculation or biological prediction."),
("cell_culture_template","Cell culture experiment planning","biology",["cell_culture_medium","cell_sample"],["biosafety_cabinet","incubator"],"L0","No cell-growth, contamination or viability model."),
("microbiology_quality_template","Microbiology quality-control planning","microbiology",["microbial_sample","reference_standard"],["biosafety_cabinet","autoclave"],"L0","No microbial identification, growth or sterility claim."),
("food_quality_template","Food quality analysis planning","food_science",["food_sample","reference_standard"],["plate_reader","analytical_balance"],"L0","No nutritional, pathogen, allergen or shelf-life result."),
("plant_growth_template","Plant growth study planning","agriculture",["plant_sample","nutrient_solution"],["greenhouse_chamber","soil_moisture_sensor"],"L0","No crop-specific growth or yield prediction."),
("soil_water_template","Soil and water sample analysis planning","environment",["soil_sample","water_sample"],["ph_meter","conductivity_meter"],"L0","No contaminant identity, potability or remediation result."),
("air_quality_template","Air quality sampling planning","environment",["air_sample","dust_sample"],["weather_station","flow_meter"],"L0","No pollutant concentration or exposure assessment."),
("water_quality_template","Water quality monitoring planning","environment",["water_sample","reference_standard"],["ph_meter","dissolved_oxygen_meter","turbidity_meter"],"L0","No compliance determination or site-specific water quality result."),
("polymer_testing_template","Polymer material characterization planning","materials",["polymer","reference_standard"],["tensile_tester","thermal_analyzer"],"L0","No polymer-specific stress-strain or thermal transition model."),
("xrd_template","X-ray diffraction analysis planning","materials",["mineral_sample"],["xray_diffractometer"],"L0","No diffraction peak prediction or phase identification."),
("thermal_material_template","Thermal material characterization planning","materials",["metal_sample","ceramic_sample"],["thermal_analyzer","thermal_chamber"],"L0","No phase transition, heat capacity or degradation result."),
("battery_test_template","Battery performance test planning","energy",["battery_cell","electrolyte_solution"],["dc_power_supply","multimeter"],"L0","No battery electrochemistry, degradation or safety model."),
("solar_cell_template","Solar cell characterization planning","energy",["solar_cell"],["solar_simulator","multimeter"],"L0","No photovoltaic efficiency or I–V prediction."),
("circuit_measurement_template","Electronic circuit measurement planning","electronics",["resistor_component","capacitor_component"],["breadboard","dc_power_supply","multimeter","oscilloscope"],"L0","Planning only; use the supported circuit solver separately for ideal circuit calculations."),
("fluid_flow_template","Fluid flow experiment planning","fluid_mechanics",["water_sample"],["centrifugal_pump","flow_meter","pressure_sensor"],"L0","No CFD, turbulence, pump curve or pressure-drop calculation."),
("aerodynamics_template","Aerodynamics test planning","fluid_mechanics",["composite_sample"],["wind_tunnel","pressure_sensor"],"L0","No drag, lift or flow-field simulation."),
("geology_template","Rock and mineral characterization planning","geoscience",["rock_sample","mineral_sample"],["seismometer","spectrometer_optical"],"L0","No mineral identification, dating or subsurface interpretation."),
("seismic_template","Seismic measurement planning","geoscience",["rock_sample"],["seismometer"],"L0","No earthquake forecast or site hazard assessment."),
("astronomy_spectra_template","Astronomical spectra observation planning","astronomy",["meteorite_sample"],["solar_telescope","spectrometer_optical"],"L0","No celestial observation, spectral inference or telescope optics simulation."),
("neuroscience_recording_template","Neural signal recording planning","neuroscience",["cell_sample"],["oscilloscope","simulation_workstation"],"L0","No neuron physiology or clinical interpretation; use the separate teaching neuron model."),
("data_analysis_template","Scientific dataset analysis planning","data_science",["reference_standard"],["simulation_workstation"],"L0","Workflow template; use the CSV analysis tools for supported data profiling."),
("microfluidics_template","Microfluidic experiment planning","engineering",["buffer","protein_sample"],["microfluidic_chip","flow_meter"],"L0","No CFD, diffusion, adsorption or biological transport model."),
("sterilization_validation_template","Sterilization process validation planning","microbiology",["microbial_sample"],["autoclave","incubator"],"L0","No validated sterilization cycle or sterility assurance level."),
("food_storage_template","Food storage study planning","food_science",["food_sample"],["refrigerator","analytical_balance"],"L0","No spoilage kinetics, pathogen growth or shelf-life determination."),
("fertilizer_leaching_template","Fertilizer and soil transport planning","agriculture",["fertilizer_sample","soil_sample"],["soil_moisture_sensor","flow_meter"],"L0","No transport, runoff, crop response or site-specific environmental assessment."),
("thermal_system_template","Thermal system test planning","energy",["coolant_sample","metal_sample"],["thermal_chamber","thermometer"],"L0","No heat-exchanger, thermal-fluid or energy-efficiency model."),
("gas_analysis_template","Gas sample analysis planning","chemistry",["gas_sample","reference_standard"],["chromatography_gc","mass_spectrometer"],"L0","No gas identification, concentration or safety result."),
("electrochemistry_template","Electrochemistry experiment planning","chemistry",["electrolyte_solution","metal_sample"],["dc_power_supply","multimeter"],"L0","No electrochemical kinetics, electrode potential or corrosion model."),
("nanomaterial_template","Nanomaterial characterization planning","materials",["nanoparticle_sample"],["spectrometer_optical","mass_spectrometer"],"L0","No particle size, morphology, toxicity or exposure result."),
]
for _id,_name,_discipline,_components,_equipment,_level,_description in _EXTRA_WORKFLOWS:
    CATALOG["workflows"].append({"id":_id,"name":_name,"discipline":_discipline,"simulation_level":_level,"required_components":_components,"required_equipment":_equipment,"description":_description})


COMPONENTS = {x["id"]: x for x in CATALOG["components"]}
EQUIPMENT = {x["id"]: x for x in CATALOG["equipment"]}
WORKFLOWS = {x["id"]: x for x in CATALOG["workflows"]}


def _number(value: Any, name: str, *, minimum: float = 0.0, strict: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")
    if value < minimum or (strict and value == minimum):
        op = "greater than" if strict else "at least"
        raise ValueError(f"{name} must be {op} {minimum}.")
    return float(value)


def validate_experiment(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("Experiment configuration must be an object.")
    workflow_id = request.get("workflow_id")
    if workflow_id not in WORKFLOWS:
        raise ValueError("Choose a supported workflow from the catalog.")
    workflow = WORKFLOWS[workflow_id]
    discipline = request.get("discipline", workflow["discipline"])
    if discipline not in {x["id"] for x in CATALOG["disciplines"]}:
        raise ValueError("Unknown discipline.")
    selected_components = request.get("components", [])
    selected_equipment = request.get("equipment", [])
    steps = request.get("steps", [])
    if not isinstance(selected_components, list) or not isinstance(selected_equipment, list) or not isinstance(steps, list):
        raise ValueError("Components, equipment and protocol steps must be lists.")
    if len(selected_components) > 30 or len(selected_equipment) > 30 or len(steps) > 40:
        raise ValueError("Configuration exceeds the supported number of items.")
    comp_ids = []
    eq_ids = []
    issues: list[dict[str, str]] = []
    for item in selected_components:
        cid = item.get("id") if isinstance(item, dict) else item
        if cid not in COMPONENTS:
            issues.append({"severity":"error","code":"unknown_component","message":f"Unknown component: {cid}"})
        elif cid not in comp_ids:
            comp_ids.append(cid)
    for item in selected_equipment:
        eid = item.get("id") if isinstance(item, dict) else item
        if eid not in EQUIPMENT:
            issues.append({"severity":"error","code":"unknown_equipment","message":f"Unknown equipment: {eid}"})
        elif eid not in eq_ids:
            eq_ids.append(eid)
    for cid in workflow["required_components"]:
        if cid not in comp_ids:
            issues.append({"severity":"error","code":"missing_component","message":f"Required component missing: {COMPONENTS[cid]['name']}"})
    for eid in workflow["required_equipment"]:
        if eid not in eq_ids:
            issues.append({"severity":"error","code":"missing_equipment","message":f"Required equipment missing: {EQUIPMENT[eid]['name']}"})
    for alternatives in workflow.get("required_equipment_options", []):
        if not any(eid in eq_ids for eid in alternatives):
            names = " or ".join(EQUIPMENT[eid]["name"] for eid in alternatives)
            issues.append({"severity":"error","code":"missing_equipment_option","message":f"Select at least one required equipment option: {names}"})
    for cid in comp_ids:
        if discipline not in COMPONENTS[cid]["disciplines"]:
            issues.append({"severity":"warning","code":"discipline_mismatch","message":f"{COMPONENTS[cid]['name']} is not catalogued for {discipline}."})
    for eid in eq_ids:
        if discipline not in EQUIPMENT[eid]["disciplines"]:
            issues.append({"severity":"warning","code":"discipline_mismatch","message":f"{EQUIPMENT[eid]['name']} is not catalogued for {discipline}."})
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or not str(step.get("action", "")).strip():
            issues.append({"severity":"error","code":"invalid_step","message":f"Protocol step {index+1} needs an action."})
        elif len(str(step.get("action", ""))) > 300:
            issues.append({"severity":"error","code":"step_too_long","message":f"Protocol step {index+1} is too long."})
    parameters = request.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError("Parameters must be an object.")
    if workflow_id == "solution_dilution":
        for key, label in [("stock_concentration_mM","Stock concentration"),("stock_volume_ml","Stock volume"),("diluent_volume_ml","Diluent volume")]:
            try: _number(parameters.get(key), label, minimum=0, strict=(key == "stock_concentration_mM" or key == "stock_volume_ml"))
            except ValueError as exc: issues.append({"severity":"error","code":"invalid_parameter","message":str(exc)})
        try:
            v1 = _number(parameters.get("stock_volume_ml"), "Stock volume", minimum=0, strict=True)
            vd = _number(parameters.get("diluent_volume_ml"), "Diluent volume")
            total = v1 + vd
            if total > 250:
                issues.append({"severity":"error","code":"vessel_capacity","message":"Total volume exceeds the selected beaker's illustrative 250 mL capacity."})
            transfer_capacities = [EQUIPMENT[eid].get("max_volume_ml", 0) for eid in eq_ids if eid in EQUIPMENT and "transfer_liquid" in EQUIPMENT[eid].get("capabilities", [])]
            max_transfer = max(transfer_capacities, default=0)
            if v1 > max_transfer:
                issues.append({"severity":"error","code":"pipette_capacity","message":f"Stock volume exceeds selected liquid-transfer equipment capacity ({max_transfer:g} mL). Select a suitable pipette or split into separately validated transfers."})
        except ValueError: pass
    if workflow_id == "enzyme_assay":
        for key, label in [("vmax","Vmax"),("km","Km"),("substrate_max","Maximum substrate concentration")]:
            try: _number(parameters.get(key), label, minimum=0, strict=True)
            except ValueError as exc: issues.append({"severity":"error","code":"invalid_parameter","message":str(exc)})
    if workflow_id == "materials_heating":
        for key, label, minimum, strict in [
            ("length_m","Bar length (m)",0,True),
            ("diffusivity_m2_s","Thermal diffusivity (m²/s)",0,True),
            ("dt_s","Time step (s)",0,True),
            ("total_time_s","Total simulation time (s)",0,True),
        ]:
            try: _number(parameters.get(key), label, minimum=minimum, strict=strict)
            except ValueError as exc: issues.append({"severity":"error","code":"invalid_parameter","message":str(exc)})
        for key, label in [("left_temp_c","Left boundary temperature"),("right_temp_c","Right boundary temperature"),("initial_temp_c","Initial temperature")]:
            try: _number(parameters.get(key), label, minimum=-273.15)
            except ValueError as exc: issues.append({"severity":"error","code":"invalid_parameter","message":str(exc)})
        nodes=parameters.get("nodes",21)
        if isinstance(nodes,bool) or not isinstance(nodes,int) or not 5 <= nodes <= 201:
            issues.append({"severity":"error","code":"invalid_parameter","message":"Number of spatial nodes must be an integer from 5 to 201."})
    if workflow_id == "epidemic_sir":
        for key, label, minimum, strict in [
            ("population","Population",0,True),
            ("initial_infected","Initial infected population",0,True),
            ("days","Simulation duration (days)",0,True),
            ("dt","Time step (days)",0,True),
            ("beta","Transmission parameter",0,False),
            ("gamma","Recovery parameter",0,False),
        ]:
            try: _number(parameters.get(key), label, minimum=minimum, strict=strict)
            except ValueError as exc: issues.append({"severity":"error","code":"invalid_parameter","message":str(exc)})
        try:
            if float(parameters.get("initial_infected",0)) >= float(parameters.get("population",0)):
                issues.append({"severity":"error","code":"invalid_population","message":"Initial infected population must be smaller than total population."})
            days=float(parameters.get("days",0)); dt=float(parameters.get("dt",0))
            if days > 1000 or dt > 1 or dt < 0.001:
                issues.append({"severity":"error","code":"invalid_time_range","message":"SIR duration must be ≤1000 days and dt between 0.001 and 1 day."})
            if dt > 0 and abs(days/dt-round(days/dt)) > 1e-8:
                issues.append({"severity":"error","code":"time_step_divisibility","message":"SIR duration must be divisible by dt (e.g. 160 days and 0.1 day)."})
        except (ValueError,TypeError):
            pass
    if workflow_id == "materials_heating" and "thermal_chamber" in eq_ids:
        chamber = EQUIPMENT["thermal_chamber"]
        for key in ("left_temp_c", "right_temp_c", "initial_temp_c"):
            val = parameters.get(key)
            if isinstance(val, (int,float)) and not isinstance(val,bool) and math.isfinite(val):
                if not chamber["temperature_min_c"] <= val <= chamber["temperature_max_c"]:
                    issues.append({"severity":"error","code":"equipment_temperature_range","message":f"{key}={val:g} °C is outside the selected thermal chamber range ({chamber['temperature_min_c']} to {chamber['temperature_max_c']} °C)."})
    errors = [x for x in issues if x["severity"] == "error"]
    return {
        "valid": not errors,
        "validation_level": workflow["simulation_level"],
        "workflow": workflow,
        "selected_components": [COMPONENTS[x] for x in comp_ids if x in COMPONENTS],
        "selected_equipment": [EQUIPMENT[x] for x in eq_ids if x in EQUIPMENT],
        "steps": [{"order":i+1,"action":str(s.get("action", "")).strip()} for i,s in enumerate(steps) if isinstance(s,dict)],
        "issues": issues,
        "summary": {"component_count":len(comp_ids),"equipment_count":len(eq_ids),"protocol_step_count":len(steps),"required_components":len(workflow["required_components"]),"required_equipment":len(workflow["required_equipment"])},
    }


def run_lab_experiment(request: dict[str, Any]) -> dict[str, Any]:
    checked = validate_experiment(request)
    if not checked["valid"]:
        raise ValueError("Experiment cannot run: resolve all validation errors first.")
    workflow_id = request["workflow_id"]
    params = request.get("parameters", {})
    results: dict[str, Any]
    if workflow_id == "solution_dilution":
        c1 = _number(params["stock_concentration_mM"], "Stock concentration", minimum=0, strict=True)
        v1 = _number(params["stock_volume_ml"], "Stock volume", minimum=0, strict=True)
        vd = _number(params["diluent_volume_ml"], "Diluent volume")
        total = v1 + vd
        results = {"calculation":"C_final = C_stock × V_stock / V_final","stock_concentration_mM":c1,"stock_volume_ml":v1,"diluent_volume_ml":vd,"final_volume_ml":total,"final_concentration_mM":c1*v1/total,"assumptions":["Ideal additive volumes.","No reaction, evaporation, density or non-ideal solution effects.","Illustrative calculator, not a validated chemistry model."]}
    elif workflow_id == "enzyme_assay":
        vmax = _number(params["vmax"], "Vmax", minimum=0, strict=True)
        km = _number(params["km"], "Km", minimum=0, strict=True)
        s_max = _number(params["substrate_max"], "Maximum substrate concentration", minimum=0, strict=True)
        points = params.get("points", 21)
        if isinstance(points, bool) or not isinstance(points, int) or not 3 <= points <= 201:
            raise ValueError("Points must be an integer from 3 to 201.")
        rows=[]
        for i in range(points):
            s=s_max*i/(points-1)
            rows.append({"substrate_concentration":s,"predicted_rate":vmax*s/(km+s)})
        results={"model":"Michaelis–Menten","columns":{"substrate_concentration":"Substrate concentration (arbitrary units)","predicted_rate":"Predicted rate (arbitrary units)"},"parameters":{"vmax":vmax,"km":km,"substrate_max":s_max,"points":points},"rows":rows,"checks":{"rates_nonnegative":all(x["predicted_rate"]>=0 for x in rows),"rate_not_above_vmax":all(x["predicted_rate"]<=vmax+1e-12 for x in rows)},"assumptions":["Illustrative model parameters.","No instrument noise, temperature dependence, enzyme deactivation or empirical fitting."]}
    elif workflow_id == "materials_heating":
        heat_params={"length_m":params.get("length_m",1.0),"diffusivity_m2_s":params.get("diffusivity_m2_s",1e-5),"left_temp_c":params.get("left_temp_c",100.0),"right_temp_c":params.get("right_temp_c",20.0),"initial_temp_c":params.get("initial_temp_c",20.0),"nodes":params.get("nodes",21),"dt_s":params.get("dt_s",1.0),"total_time_s":params.get("total_time_s",1000.0)}
        results=execute_model("heat_diffusion_1d",heat_params)
        results["computed_scientific_result"]=True
        results["assumptions"]=["Explicit finite-difference solver for 1D homogeneous material.","Fixed boundary temperatures and constant thermal diffusivity.","No phase change, convection, radiation or material heterogeneity."]
    elif workflow_id == "epidemic_sir":
        sir_params={"population":params.get("population",10000),"beta":params.get("beta",0.3),"gamma":params.get("gamma",0.1),"initial_infected":params.get("initial_infected",10),"days":params.get("days",160),"dt":params.get("dt",0.1)}
        results=execute_model("sir_epidemic",sir_params)
        results["computed_scientific_result"]=True
        results["assumptions"]=["Homogeneous mixing and fixed transmission/recovery parameters.","Illustrative compartment model, not fitted to local data.","Not for public-health decisions or individual prediction."]
    else:
        results={"execution":"workflow_only","message":"The protocol has been validated and recorded, but no scientific solver is connected to this workflow yet.","computed_scientific_result":False}
    return {
        "experiment_id":"lab-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        "created_at":datetime.now(timezone.utc).isoformat(),
        "name":str(request.get("name", "Untitled virtual experiment"))[:160],
        "research_question":str(request.get("research_question", ""))[:1000],
        "discipline":request.get("discipline", checked["workflow"]["discipline"]),
        "workflow_id":workflow_id,
        "validation_level":checked["validation_level"],
        "configuration":{"components":[x["id"] for x in checked["selected_components"]],"equipment":[x["id"] for x in checked["selected_equipment"]],"steps":checked["steps"],"parameters":params},
        "validation":checked,
        "results":results,
        "provenance":{"software":"Virtual Lab Platform v1.6","model_status":"illustrative demonstration","scientific_validation":"not established","configuration_recorded":True},
        "limitations":["Equipment inventory metadata is illustrative and does not represent a vendor-validated digital twin.","Only explicitly supported workflow calculators and connected solvers produce numerical outputs.","No result substitutes for physical measurement or expert review."],
    }
