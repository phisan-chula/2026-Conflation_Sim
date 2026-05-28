import os
import subprocess
import shutil
import sys

def run_scenario(scenario_name, sim_args=[]):
    """
    Executes the 4-step processing pipeline sequentially under specific parameters,
    then automatically archives and renames the output directory from './RESULT'.
    """
    print("=" * 80)
    print(f"RUNNING SCENARIO: {scenario_name}")
    print("=" * 80)
    
    # Define the 4 sequential execution steps
    pipeline_steps = [
        ["python", "1_SimuParcel.py"] + sim_args,
        ["python", "2_Align_Transf.py"],
        ["python", "3_global_warp.py"],
        ["python", "4_vertex_conflation.py"]
    ]
    
    # Execute each pipeline script in sequence
    for step in pipeline_steps:
        print(f"\n[EXEC] Executing: {' '.join(step)}")
        # run with check=True to raise an exception immediately if a script fails
        subprocess.run(step, check=True)
        
    # Define the final target backup location
    target_backup_dir = os.path.join(".", scenario_name)
    
    # Clean up previous runs of this scenario to prevent file permission/overwrite locks
    if os.path.exists(target_backup_dir):
        print(f"[IO] Cleaning up existing stale directory: {target_backup_dir}")
        shutil.rmtree(target_backup_dir)
        
    # Safeguard and rename the generated output folder
    if os.path.exists("./RESULT"):
        print(f"[IO] Renaming generated folder: './RESULT' -> '{target_backup_dir}'")
        shutil.move("./RESULT", target_backup_dir)
        print(f"\n[SUCCESS] Scenario '{scenario_name}' successfully built and archived.\n")
    else:
        print(f"[ERROR] Expected folder './RESULT' was not found! Aborting pipeline.")
        sys.exit(1)


if __name__ == "__main__":
    # Define the 4 explicit run parameters requested
    scenarios = [
        {
            "name": "RESULT_NEAT",
            "args": []  # No option (default simulation noise baseline)
        },
        {
            "name": "RESULT_ID01",
            "args": ["-m", "1:-2,-4"]  # ID 1 shifted by dx=-2, dy=-4
        },
        {
            "name": "RESULT_ID20",
            "args": ["-m", "20:2,4"]  # ID 20 shifted by dx=+2, dy=+4 (matching 1_SimuParcel parsing format)
        },
        {
            "name": "RESULT_ID01_ID20",
            "args": ["-m", "1:-2,-4", "20:2,4"]  # Combined multi-point compounding shifts
        }
    ]
    
    try:
        # Loop through each scenario mapping configuration and execute
        for sc in scenarios:
            run_scenario(sc["name"], sc["args"])
            
        print("=" * 80)
        print("ALL 4 PIPELINE SCENARIOS COMPLETED SUCCESSFULLY.")
        print("=" * 80)
        
    except subprocess.CalledProcessError as err:
        print("\n" + "!" * 80)
        print(f"CRITICAL ERROR: A pipeline sub-script crashed during execution!")
        print(f"Failed command: {' '.join(err.cmd)}")
        print("!" * 80)
        sys.exit(1)
