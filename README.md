openstack-helper - A command-line tool to assist in OpenStack cloud administration.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## About

This script helps with the administration of an OpenStack environment.
While the OpenStack CLI is powerful, this script complements it by providing
additional advanced commands and reports for enhanced administrative insights.
It does not create or update any resources and can be used with read-only users.
The tool uses the Rich library to present information in a visually appealing and
user-friendly manner. The Rich library is packaged in most Linux distributions,
allowing installation via package managers like apt, yum, or pacman. It can also
be installed using pip.



## Usage

Display the global help message:

```bash
$ openstack-helper --help
usage: openstack-helper [-h] [--debug]
                        {unused_ports,up,images_usage,iu,resource_provider,rp,check_allocations,ca} ...

OpenStack Helper tool

positional arguments:
  {unused_ports,up,images_usage,iu,resource_provider,rp,check_allocations,ca}
    unused_ports (up)   Retrieves and checks unused OpenStack ports
    images_usage (iu)   Show usage details about images, including which VMs are
                        using them.
    resource_provider (rp)
                        Retrieves and displays inventory and usage details about
                        resource providers
    check_allocations (ca)
                        Check instance allocation in Nova and Placement

options:
  -h, --help            show this help message and exit
  --debug, -d           debug flag

    Example of use:
        openstack-helper --help
        openstack-helper rp --help
        openstack-helper rp --resource-class vcpu --sort-by "Current Alloc Ratio"
        openstack-helper unused_ports -h
        openstack-helper unused_ports --network-id 17583b07-92c2-4a07-9fb9-5bc8705d58e2

```

Get help for a specific subcommand:

```bash
$ openstack-helper iu --help
usage: openstack-helper images_usage [-h] [--name NAME] [--image-id IMAGE_ID]
                                     [--tag TAG] [--days DAYS] [--current-project]
                                     [--show-no-vms] [--show-vm-details]

options:
  -h, --help           show this help message and exit
  --name NAME          Filter images by name
  --image-id IMAGE_ID  Filter images by ID
  --tag TAG            Filter images by tag(s). Multiple tags can be specified,
                       separated by commas. Only images containing all specified tags
                       are included
  --days DAYS          Show only images that are at least X days old
  --current-project    Restrict server lookup to the currently scoped project
                       (otherwise, all projects are included)
  --show-no-vms        Show only images that have zero VMs using them
  --show-vm-details    Display detailed VM information (IDs and names)

$ openstack-helper rp --help
usage: openstack-helper resource_provider [-h] [-r [{VCPU,MEMORY_MB,DISK_GB} ...]]
                                          [-s SORT_BY [SORT_BY ...]] [--name NAME]
                                          [--uuid UUID] [--aggregates-uuid MEMBER_OF]

options:
  -h, --help            show this help message and exit
  -r, --resource-class [{VCPU,MEMORY_MB,DISK_GB} ...]
                        Show information only for the specified resource classes. You
                        can specify multiple classes by separating them with a space
                        (for example: '-r VCPU MEMORY_MB'). (default: all)
  -s, --sort-by SORT_BY [SORT_BY ...]
                        Sort table by the specified column(s). You can specify
                        multiple columns by separating them with spaces (for example:
                        "-s 'Used' 'Provider Name'").(default: ['Provider Name'])
  --name NAME           Filter by resource provider name
  --uuid UUID           Filter by resource provider UUID
  --aggregates-uuid MEMBER_OF
                        Filter by aggregates UUIDs. When specifying multiple UUIDs,
                        separate them with commas

```

## Authentication Methods

##### Environment Variables

You can manually set the required environment variables or use an OpenStack RC file to simplify the process.

```bash
$ source openstack.rc
```

##### clouds.yaml Configuration
Alternatively, you can use a *clouds.yaml* and export "*OS_CLOUD*" variable to pass the cloud name.

For more information: https://docs.openstack.org/python-openstackclient/latest/cli/man/openstack.html

## Installation

Clone or download the repository to your local machine.

#### Development mode using pip
```bash
$ pip install -e .
```

#### Development mode using pipx
```bash
$ pipx install -e .
```
## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
