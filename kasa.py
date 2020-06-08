from apama.eplplugin import EPLAction, EPLPluginBase, Correlator, Event, Any
from kasa import Discover
import asyncio, threading, queue

class Job(object):
	def __init__(self, fn):
		self.fn = fn

def iothread(plugin):
	plugin.getLogger().info("iothread")
	while plugin.running:
		try:
			job = plugin.queue.get(timeout=1.0)
			plugin.getLogger().info("running job")
			job.fn()
			plugin.getLogger().info("job done")
		except queue.Empty:
			pass

	plugin.getLogger().info("iothread done")

class KasaPluginClass(EPLPluginBase):

	def __init__(self, init):
		super(KasaPluginClass, self).__init__(init)
		self.getLogger().info("KasaPluginClass.__init__")
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
		self.getLogger().info("KasaPluginClass.sendResponseEvent")
		Correlator.sendTo(channel, Event(eventType, body))

	@EPLAction("action<>")
	def shutdown(self):
		self.getLogger().info("KasaPluginClass.shutdown")
		self.running = False
		self.thread.join()

	@EPLAction("action<integer, string>")
	def discoverDevices(self, requestId, channel):
		self.getLogger().info("KasaPluginClass.discoverDevices")
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":Any("sequence<kasa.Device>", [self._createDeviceEvent(addr, dev) for addr, dev in asyncio.run(Discover.discover()).items()]),
			})
		))

	@EPLAction("action<string, integer, string>")
	def createDeviceObject(self, address, requestId, channel):
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":Any("kasa.Device", self._createDeviceEvent(address, asyncio.run(Discover.discover_single(address)))),
			})
		))

	@EPLAction("action<string, boolean, integer, string>")
	def devicePower(self, address, state, requestId, channel):
		self.queue.put(Job(
			lambda: self._sendResponseEvent(channel, "kasa.Response", {
				"requestId":requestId,
				"data":asyncio.run(self.devices[address].turn_on() if state else self.devices[address].turn_off()),
			})
		))



