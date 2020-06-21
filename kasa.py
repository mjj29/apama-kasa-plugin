from apama.eplplugin import EPLAction, EPLPluginBase, Correlator, Event, Any
from kasa import Discover
import asyncio, threading, queue

class Job(object):
	"""
		Jobs to be executed asynchronously
		@param fn a functor to execute
	"""
	def __init__(self, fn):
		self.fn = fn

def iothread(plugin):
	"""
		Background thread to execute async jobs on.
	"""
	plugin.getLogger().debug("Starting background IO thread for asynchronous jobs")
	while plugin.running:
		try:
			job = plugin.queue.get(timeout=1.0)
			job.fn()
		except queue.Empty:
			pass

	plugin.getLogger().info("iothread done")

class KasaPluginClass(EPLPluginBase):
	"""
		The Python EPL plugin for managing Kasa devices
	"""
	def __init__(self, init):
		super(KasaPluginClass, self).__init__(init)
		self.getLogger().info("Starting Kasa plug-in")
		self.running = True
		self.devices = {}
		self.queue = queue.SimpleQueue()
		self.thread = threading.Thread(target=iothread, args=[self], name='Apama KasaPluginClass io thread')
		self.thread.start()

	def _createDeviceEvent(self, addr, dev):
		asyncio.run(dev.update())
		self.devices[addr] = dev;
		return Event("kasa.Device", {
			"address":addr, 
			"id":dev.device_id, 
			"powerState":dev.is_on,
			"model":dev.model,
			"deviceType":str(dev.device_type),
			"sysinfo":dev.sys_info,
			"hwinfo":dev.hw_info,
		})

	def _sendResponseEvent(self, channel, eventType, body):
		Correlator.sendTo(channel, Event(eventType, body))

	@EPLAction("action<>")
	def shutdown(self):
		"""
			Plug-in function to shutdown the background thread.
		"""
		self.getLogger().debug(f"Shutting down Kasa plug-in")
		self.running = False
		self.thread.join()

	@EPLAction("action<integer, string>")
	def discoverDevices(self, requestId, channel):
		"""
			Discover all devices on the network and send a Response event containing all of the devices.
		"""
		self.getLogger().debug(f"Discovering devices")
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":Any("sequence<kasa.Device>", [self._createDeviceEvent(addr, dev) for addr, dev in asyncio.run(Discover.discover()).items()]),
			})
		))

	@EPLAction("action<string, integer, string>")
	def update(self, address, requestId, channel):
		"""
			Look up a device with a given address.
		"""
		self.getLogger().debug(f"Looking for device with address {address}")
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":Any("kasa.Device", self._createDeviceEvent(address, self.devices[address])),
			})
		))


	@EPLAction("action<string, integer, string>")
	def createDeviceObject(self, address, requestId, channel):
		"""
			Look up a device with a given address.
		"""
		self.getLogger().debug(f"Looking for device with address {address}")
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":Any("kasa.Device", self._createDeviceEvent(address, asyncio.run(Discover.discover_single(address)))),
			})
		))

	@EPLAction("action<string, boolean, integer, string>")
	def devicePower(self, address, state, requestId, channel):
		"""
			Turn the device on or off.
		"""
		self.getLogger().debug(f"Turning {'on' if state else 'off'} device with address {address}")
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":asyncio.run(self.devices[address].turn_on() if state else self.devices[address].turn_off()),
			})
		))

	@EPLAction("action<string, integer, string, integer, integer>")
	def setColorTemp(self, address, requestId, channel, kelvin, ms):
		"""
			Set the color temp on the device.
		"""
		self.getLogger().debug(f"Setting color temp to {kelvin}K on device with address {address}")
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":asyncio.run(self.devices[address].set_light_state({"color_temp":kelvin}))
			})
		))

	@EPLAction("action<string, integer, string, integer, integer>")
	def setBrightness(self, address, requestId, channel, brightness, ms):
		"""
			Set the brightness on the device.
		"""
		self.getLogger().debug(f"Setting brightness to {brightness}% on device with address {address}")
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":asyncio.run(self.devices[address].set_light_state({"brightness":brightness}))
			})
		))

	@EPLAction("action<string, integer, string, integer, integer, integer, integer>")
	def setHSV(self, address, requestId, channel, hue, saturation, value, ms):
		"""
			Set the color on the device.
		"""
		self.getLogger().debug(f"Setting color to {hue},{saturation},{value} on device with address {address}")
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":asyncio.run(self.devices[address].set_light_state({"hue":hue, "saturation":saturation, "value":value, "color_temp":0}))
			})
		))

	@EPLAction("action<string, integer, string, integer, boolean>")
	def setChildPowerState(self, address, requestId, channel, child, state):
		"""
			Set the power state on a child
		"""
		self.getLogger().debug(f"Setting power state on {child} to {state} on device with address {address}")
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":asyncio.run(self.devices[address].children[child].turn_on() if state else self.devices[address].children[child].turn_off())
			})
		))

