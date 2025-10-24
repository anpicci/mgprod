#IMPORTANT: The workers that are submitted to this lobster master, MUST come from T3 resources

import datetime
import os
import sys

from lobster import cmssw
from lobster.core import AdvancedOptions, Category, Config, MultiProductionDataset, StorageConfiguration, Workflow

tstamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')

# events_per_gridpack = 15e6
events_per_gridpack = 50e3
events_per_lumi = 500

# run_setup = "full_production"
# run_setup = "mg_studies"
run_setup = "lobster_test"

year = "2022"
# year = "2022EE"
# year = "2023"
# year = "2023BPix"

version = f"v{tstamp}"
grp_tag = "test"
prod_tag = "Round1/Batch1"

master_label = f"EFT_T3_{tstamp}"

if run_setup == "mg_studies":
    # For MadGraph test studies
    output_path  = f"/store/user/$USER/LHE_step/{grp_tag}/{version}"
    workdir_path = f"/tmpscratch/users/$USER/LHE_step/{grp_tag}/{version}"
    plotdir_path = f"~/www/lobster/LHE_step/{grp_tag}/{version}"
elif run_setup == "full_production":
    # For Large MC production
    output_path  = f"/store/user/$USER/FullProduction/Run3/{year}/{grp_tag}/LHE_step/{version}"
    workdir_path = f"/tmpscratch/users/$USER/FullProduction/Run3/{year}/{grp_tag}/LHE_step/{version}"
    plotdir_path = f"~/www/lobster/FullProduction/Run3/{year}/{grp_tag}/LHE_step/{version}"
elif run_setup == "lobster_test":
    # For lobster workflow tests
    grp_tag = f"lobster_{tstamp}"
    output_path  = f"/store/user/$USER/LHE_step/tests/{grp_tag}"
    workdir_path = f"/tmpscratch/users/$USER/LHE_step/tests/{grp_tag}"
    plotdir_path = f"~/www/lobster/LHE_step/tests/{grp_tag}"
else:
    raise ValueError(f"Unknown run setup, {run_setup}")

input_path = "/store/user/"

storage = StorageConfiguration(
    input = [
        "file:///cms/cephfs/data" + input_path,
        #"root://skynet013.crc.nd.edu:1094/" + input_path,
        # "root://skynet013.crc.nd.edu:1096/" + input_path, # For outside-of-ND file access
    ],
    output = [
        "file:///cms/cephfs/data" + output_path,
        #"root://skynet013.crc.nd.edu:1094/" + output_path,
    ],
    disable_input_streaming=True
)

wf_steps = ["lhe"]
fragment_map = {
    "2022": {
        "lhe": "run3_cfgs/2022_LHE_cfg.py"
    },
    "2022EE": {
        "lhe": "run3_cfgs/2022EE_LHE_cfg.py"
    },
    "2023": {
        "lhe": "run3_cfgs/2023_LHE_cfg.py"
    },
    "2023BPix": {
        "lhe": "run3_cfgs/2023BPix_LHE_cfg.py"
    },
}

event_multiplier = {
    "default": 1.0,
    "ttHJet": 2.5,
    "ttllNuNuJetNoHiggs": 3.5,
    "ttlnuJet": 2.5,
}

gridpacks = [
    #"example/path/to/gridpack/location/ttHJet_all22WCsStartPtCheckdim6TopMay20GST_run0_slc7_amd64_gcc630_CMSSW_9_3_16_tarball.tar.xz"
    "awightma/gridpack_scans/run3/tests/ttHJet_ctWReTest13p6AxisScan_run0_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz"
]

category_resources = {
    "default": {
        "cores": 1,
        "memory": 3000,
        "disk": 4500,
    },
    # Example for a process (called 'example') that needs tailored resources
    # "lhe_example": {
    #     "cores": 1,
    #     "memory": 2000,
    #     "disk": 4000,
    # }
}

wfs = []

print("Generating Workflows")
for idx,gp in enumerate(gridpacks):
    head,tail = os.path.split(gp)
    arr = tail.split("_")

    # Ex: p = "ttHJet", c = "all22WCsStartPtCheckdim6TopMay20GST", r = "run0"
    p,c,r = arr[0:3]
    label = f"lhe_step_{p}_{c}_{r}"


    category = f"lhe_{p}"
    if category in category_resources:
        wf_resources = category_resources[category]
    else:
        # Use the default resources
        wf_resources = category_resources["default"]
    cat = Category(name=category,**wf_resources)

    wf_fragments = {}
    for step in wf_steps:
        if year == None:
            pass
        else:
            wf_fragments[step] = fragment_map[year][step]

    multiplier = event_multiplier["default"]
    if p in event_multiplier:
        multiplier = event_multiplier[p]
    nevents = int(multiplier*events_per_gridpack)
    print(f"\t[{idx+1}/{len(gridpacks)}] Gridpack: {tail} (nevts {nevents})")

    if year in ["2022","2022EE"]:
        rel = "CMSSW_12_4_14_patch3"
    elif year in ["2023","2023BPix"]:
        rel = "CMSSW_13_0_13"
    else:
        raise RuntimeError(f"Invalid year {year}")

    cfg = wf_fragments["lhe"]
    lhe = Workflow(
        label=label,
        command=f"cmsRun {cfg}",
        sandbox=cmssw.Sandbox(release=rel),
        merge_size=-1,  # Don't merge the output files, to keep individuals as small as possible
        cleanup_input=False,
        globaltag=False,
        outputs=["LHE-00000.root"],
        dataset=MultiProductionDataset(
            gridpacks=gp,
            events_per_gridpack=nevents,
            events_per_lumi=events_per_lumi,
            lumis_per_task=1,
            randomize_seeds=True
        ),
        category=cat
    )
    wfs.extend([lhe])

config = Config(
    label=master_label,
    workdir=workdir_path,
    plotdir=plotdir_path,
    storage=storage,
    workflows=wfs,
    advanced=AdvancedOptions(
        bad_exit_codes=[127, 160],
        log_level=1,
        payload=10,
        osg_version="3.6",  # Possibly needed if using Run2 CMSSW release
        # xrootd_servers=["skynet013.crc.nd.edu:1094"]
    )
)
