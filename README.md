# QPEP

QPEP is an encrypted performance enhancing proxy designed to protect high-latency satellite connections without TCP performance degradation. QPEP leverages a QUIC-tunnel to encapsulate TCP traffic over the satellite hop and de-encapsulate it on an internet connected server.

In conjunction with QPEP, this repository also contains a dockerized testbed based on the OpenSAND satellite networking simulation engine. Built into this testbed are pre-configured installations of QPEP and other comparable technologies for benchmarking and experimentation.

## Getting Started
These instructions will help you get QPEP configured and running inside the dockerized testbed. The QPEP testbed has been extensively tested on Windows 10 Professional Edition (with Hyper-V & Docker) but will likely cooperate on *nix systems as well.

:warning: Disclaimer: While it is possible to configure and run QPEP outside of the testbed environment, this is discouraged for anything other than experimental testing. The current release of QPEP is a proof-of-concept research tool and, while every effort has been made to make it secure and reliable, it has not been vetted sufficiently for its use in critical satellite communications. Commercial use of this code is not only forbidden under the terms of its license, but would also be exceptionally foolhardy. When QPEP reaches a more mature state, this disclaimer will be updated.

### Prerequisites
Ensure that you have all of the following prerequisites on your machine:
* [Docker & Docker-Compose](https://docs.docker.com/compose/install/) (_tested on Docker Desktop for Windows (v2.2.0), Engine (v1.25.2), Compose (v1.25.2)_)
* Python 3.7+
* [Python pip](https://www.pypa.io/en/latest/)
* An XServer for the OpenSAND GUI (e.g. [VcXsrv](https://sourceforge.net/projects/vcxsrv/) for Windows)
* git

### Installing
These instructions are for Docker on Windows. *nix systems should be essentially the same except that setting up the XServer may require a different approach (for example, see [this guide](https://medium.com/@SaravSun/running-gui-applications-inside-docker-containers-83d65c0db110) for Ubuntu).

First, create a new directory and clone this github repository into it.
```
> mkdir C:\qpep
> cd C:\qpep
> git clone https://github.com/pavja2/qpep
```
Create a python3 virtualenv inside the directory and use pip to install necessary python dependencies ([docker-py](https://pypi.org/project/docker/), [loguru](https://pypi.org/project/loguru/) and [nclib](https://pypi.org/project/nclib/)):
```
> cd C:\qpep
> python -m venv venv
> venv\Scripts\activate
> cd qpep\opensand-testbed
> pip install -r requirements.txt 
```
Ensure your XServer is running and accessible from the docker client. For example, on Windows you can open a remotely accessible VcxServer as follows: 
```
Start->XLaunch
Set "Display Number" to 0 -> Next
Set "Start No Client" -> Next
Check "Disable access control" -> Next -> Finish
```
Finally, enter the opensand-testbed directory and run "browser_examples.py." You will need to provide an IP address that routes to your local machine's X server but is not 127.0.0.1 or localhost (it must be routable from within Docker). Generally, you can find this with ```ipconfig``` on Windows or ``ifconfig`` on *nix:
```
cd C:\qpep\qpep\opensand-testbed
python browser_examples.py --scenario qpep [HOST_IP]
```
The first time you run this, it may take a while to build the docker containers. Eventually, the OpenSAND GUI and a web-browser connected to the satellite network will launch. Congrats! You are now connected to a simulated encrypted satellite network. 

**Note:** If the script freezes at the message "Starting Opensand Platform" for more than a minute or two this is almost always a result of the docker container being unable to connect to an XServer. OpenSAND requires a GUI and fails silently without one. Double-check that you have set your XServer options correctly and run the python script again.

## Using the Testbed
### Simple Browsing
The provided browser_examples.py python script allows you to open a quipzilla browser instance connected to the satellite customer terminal and visit real-world websites over a simulated satellite connection. You can test several different scenarios. 

To change from a GEO latency simulation to a LEO variable latency simulation use the orbit flag:
```
   python browser_examples.py --orbit LEO --scenario QPEP [HOST_IP]
```                                                                

To test other encryption and PEP tools than QPEP, change the scenario. The following scenario options are available:
* ```plain``` A satellite network with no optimizations
* ```pepsal_integrated``` A satellite network with the unencrypted [PEPsal](https://github.com/danielinux/pepsal) proxy installed on the satellite terminal network
* ```pepsal_distributed``` A satellite network with the unencrypted [PEPsal](https://github.com/danielinux/pepsal) proxy installed on both the satellite terminal and gateway networks
* ```qpep``` A satellite network with this repository's encrypted QPEP proxy installed on both the satellite terminal and gateway networks
* ```open_vpn``` A satellite network with the encrypted VPN [OpenVPN](https://openvpn.net/) installed on both the satllite terminal and gateway networks

For more configuration options and help use the ```-h``` flag:
```
usage: browser_examples.py [-h] [--display DISPLAY]
                           [--scenario {plain,qpep,pepsal_distributed,pepsal_integrated,open_vpn}]```
                           [--orbit {GEO,LEO}] [--wireshark]
                           xhost

positional arguments:
  xhost                 The host IP address of an accessible XServer. Note:
                        this must be accessible from within the docker testbed```
                        (so localhost or 127.0.0.1 will not work).Give an example

optional arguments:
  -h, --help            show this help message and exit### And coding style tests
  --display DISPLAY     The display number of an accessible XServer (default:
                        0)Explain what these tests test and why
  --scenario {plain,qpep,pepsal_distributed,pepsal_integrated,open_vpn}
                        The PEP scenario you wish to evaluate (default: plain)```
  --orbit {GEO,LEO}     The orbit you want to simulate the satellite locationGive an example
                        delay for (default: GEO)```
  --wireshark           Add this flag to launch a wireshark instance on the
                        simulated satellite.
```
### Benchmarking
The provided testbed also comes with support for writing and running custom benchmarking scenarios in python. Examples of many of these scenarios - including more complicated ones - can be found in the file ```simulation_examples.py```

#### Example: Testing Page Load Times with Browsertime
This example shows how to compare page load times between QPEP and a network with no performance enhancing proxy installed. A similar approach should work for most benchmarks and scenarios included in the testbed.

First, you will need to import a testbed from ```testbeds.py```, any scenarios (proxies, VPNs, etc) you wish to test from ```scenarios.py```, and any benchmarks from ```benchmarks.py```:
```python
from testbeds import BasicTestbed
from scenarios import QPEPScenario, PlainScenario
from benchmakrs import SitespeedBenchmark
```
Next, you will need to initialize that testbed - being careful to provide the correct host and display number for your XServer GUI:
```python
my_testbed = BasicTestbed(host_ip='192.168.0.4', display_number=0)
```
Next, define your benchmarks and scenarios - check out the comments in benchmarks.py for details on benchmark-specific options:
```python
import copy #this lets us define a list of benchmarks and use it everywhere

my_benchmarks = [SitespeedBenchmark(hosts=["https://www.google.com", "https://www.wikipedia.org", "https://www.tmall.com"], iterations=3)]

plain_scenario = PlainScenario(name="Plain PLTs", testbed=my_testbed, benchmarks=copy.deepcopy(my_benchmarks))
qpep_scenario = PlainScenario(name="Plain PLTs", testbed=my_testbed, benchmarks=copy.deepcopy(my_benchmarks))
```                                                                                                          
Next, you can run your scenarios and their benchmarks:
```python 
plain_scenario.run_benchmarks()
qpep_sceanrio.run_benchmarks()
```
If you have a large number of benchmarks you'd like to try and want to avoid restarting OpenSAND between each scenario, you can pre-deploy the scenario and then run all of the benchmarks inside it. This is also useful if you would like to manually change settings in the OpenSAND GUI before running a particular benchmark.
```python
plain_scenario.deploy_scenario()
plain_scenario.run_benchmarks(deployed=True)
``` 
You can easily access the benchmark results programmatically or have them print to console:
```python
plain_scenario.benchmarks[0].results # scenario has a list of benchmarks with a results dictionary property
qpep_scenario.print_results() # you can also print a formatted summary of all benchmarks to the console directly
``` 
### Doing Other Stuff
The provided python scripts (especially ```simulation_examples.py```) provide many examples of the sort of things you can do within the QPEP testbed. However if you wish to do more, you can always directly access the docker containers within a scenario context. The following containers are available:
* ```satellite``` The satellite itself. Has Wireshark installed and GUI support so you can easily inspect traffic on the ```opensand_tun``` interface and see how it is encapsulated/encrypted over-the-air. You can also launch wireshark from python with ```testbed.launch_wireshark()```
* ```gateway``` The satellite groundstation. Can either route traffic to/from other docker-containers (e.g. ```ws-gw```, the gateway workstation) on a simulated LAN or to the real internet.
* ```terminal``` The satellite user terminal. Can route traffic to/from other docker-containers (e.g. ```ws-st```, the satellite terminal workstation) on a simulated LAN.
* ```ws-ovpn``` A workstation with an OpenVPN server installed. Is situated local to the ```gateway``` network.
* ```sitespeed``` A workstation with the [Browsertime](https://github.com/sitespeedio/browsertime) benchmarking tool installed. Is situated local to the ```terminal``` network. To connect it to the terminal router in python, use ```testbed.connect_sitespeed_workstation()```
* ```ws-st``` A workstation on the ```terminal``` network. It contains the web browser ```qupzilla``` and supports GUI applications. To connect it to the terminal router in a python script run ```testbed.connect_terminal_workstation()```. You can launch the web browser from python as well with ```testbed.launch_web_browser()```

All containers have bash installed and can be accessed directly from docker-compose as well. First, start the testbed in python with ```testbed.start_testbed()``` and deploy any specific scenario with ```scenario.deploy_scenario()```. Then open a console and navigate to the testbed directory to access the containers. For example, to download a web-page using wget:
* First, in Python:
```python
from testbeds import BasicTestbed
from scenarios import PlainScenario
my_testbed = BasicTestbed(host=[HOST_IP], display=0)
plain_scenario = PlainScenario(name="Wget Plain", testbed=my_tesbed, benchmarks=[])
plain_scenario.deploy_scenario()
```
* Second, in your shell:
```
> cd C:\qpep\qpep\opensand-testbed
> docker-compose exec ws-st bash
$ wget https://www.google.com 
```
**Note:** One thing which can cause trouble is stopping the OpenSAND scenario once it has launched. This breaks the ip-routes between containers in the network, causing traffic to be unroutable in some cases - even after you restart the scenario. Most of the time running ```scenario.deploy_scenario(testbed_up=True)``` is sufficient to fix this. However, PEPsal takes over network routes at a lower level and can prevent the py-docker library from communicated with containers. See the ```attenuation_test_pepsal_scenario``` method in ```simulation_examples.py``` for an example of how to run PEPsal under custom OpenSAND conditions programmtically.  

## Built With

## Contributing

## Authors

## License

## Acknowledgments