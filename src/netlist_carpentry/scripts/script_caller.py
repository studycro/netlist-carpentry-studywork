import shutil
import subprocess
from typing import Dict, List, Optional, Union

from netlist_carpentry import ON_WINDOWS


def call(cmds: List[str], verbose: bool, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess[str]:
    formatted_cmds: Union[str, List[str]] = cmds if ON_WINDOWS else ' '.join(cmds)
    executable = shutil.which('bash') if not ON_WINDOWS else None
    return subprocess.run(formatted_cmds, shell=not ON_WINDOWS, capture_output=not verbose, text=True, env=env, executable=executable)
