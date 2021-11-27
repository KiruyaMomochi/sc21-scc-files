# SC21 SCC Files

Here are some files and scripts we used in [SC21 Student Cluster Competition](https://studentclustercompetition.us/2021/Teams/ShanghaiTechUniversity/index.html).

## Cloud-Init

`default.yml.j2` is our cloud-init file, which is used to configure Azure instances.

- We use a systemd drop-in file, to fix omsagent confliction with cloud-init.
- `rdma.py`: RDMA IPoIB address provided in `/var/lib/hyperv/.kvp_pool_0` does not contains our machine's RDMA MAC, so we use address provided in `/var/lib/waagent/SharedConfig.xml`.

## CycleCloud

`cycle.psm1` is a PowerShell module for interacting with CycleCloud API, to initialize, run `Set-CycleCloudConfig` cmdlet first.

## Misc

`ofed.psm1` is another PowerShell module for simplify downloading latest Mellanox OFED driver.
It provides cmdlet with tab completion of `Get-OfedDownloadInfo`, `Get-OfedArches`, etc.
