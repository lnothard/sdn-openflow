from mininet.topo import Topo
from mininet.link import TCLink

class EcmpTopology(Topo):
  hosts_ = []
  switches_ = []

  def build(self):
    self.newSwitch(numHosts=3)
    self.newSwitch(numHosts=1, numLinks=3, bw=100, delay='5ms')
    self.newSwitch(numHosts=3, numLinks=2, bw=50, delay='10ms')

  def newSwitch(self, numHosts, numLinks=None, bw=None, delay=None):
    self.switches_.append(s := self.addSwitch(f"s{len(self.switches_) + 1}"))
    for i in range(0, numHosts):
      self.hosts_.append(h := self.addHost(f"h{len(self.hosts_) + 1}"))
      self.addLink(s, h)

    if not numLinks: return
    for i in range(0, numLinks):
      self.addLink(s, self.switches_[self.switches_.index(s) - 1],
                   cls=TCLink, bw=bw, delay=delay)

topos = {
  'ecmpTopology': (lambda: EcmpTopology())
} 