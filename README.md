# apama-kasa-plugin
Apama EPL plug-in for talking to TP Link Kasa devices

## Prerequisites

This plug-in works with Apama 10.5 or later. You can download Apama from http://apamacommunity.com/ . You will also need to add the Kasa module to the Python in your Apama installation, either by adding a virtual environment, or by installing it from an Apama command prompt:

    pip install python-kasa

## Using this plug-in from EPL

To use this plug-in to control Kasa devices from EPL, first you need to add the plug-in to your correlator configuration YAML:

	eplPlugins:
	   KasaPlugin:
	      pythonFile: "${PARENT_DIR}/kasa.py"
	      class: KasaPluginClass

Secondly, add `Kasa.mon` to your project.

Next you need to get a `kasa.Device` event using one of the static actions on `kasa.Kasa`. These events are all asynchronous and you must listen for a `kasa.Response` event with the matching `requestId` field as returned by the action.

To search for devices:

	on kasa.Response(requestId=kasa.Kasa.discover()) as resp {
		kasa.Device dev;
		for dev in <sequence<kasa.Device> > resp.data {
			// do something with the device
		}
	}

If you already know the address of the device you can look it up by address or host name:

	on kasa.Response(requestId=kasa.Kasa.device("officelight")) as resp {
		kasa.Device dev := <kasa.Device> resp.data;
		// do something with the device
	}

`kasa.Device` events have information about the device and methods to interact with them. The actions also follow the similar response pattern. For example:

	on kasa.Response(requestId=dev.togglePowerState()) {
		// power toggle has no response data
	}

## Documentation

ApamaDoc documentation can be found in the doc sub directory.

## Licence

The Apama EPL Kasa Plug-in is licensed under the Apache 2.0 license.
