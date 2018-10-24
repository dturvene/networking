#!/usr/bin/env python
"""
Network Probe utility

"""

import sys
from socket import AF_INET
from time import sleep

from IEEE import MAC_addr
from pyroute2 import IW, IPRoute, NetlinkError
from pyroute2.netlink import nl80211
import ipaddress

import unittest
import urllib2

# inline breakpoint
from pdb import set_trace as bp

class NmException(Exception):
    def __init__(self, descr):
        self.descr = descr

class NetProbe(object):
    '''
    control
    '''
    
    def __init__(self, **keyargs):

        self.ipr = IPRoute()
        
        self.mac_addr = MAC_addr()
        self.ipv4_net = ipaddress.ip_network('192.168.3.0/24')
        self.ipv4_addr = self.ipv4_net[100]
        self.ifname = 'wlp4s0'
        self.iftype = nl80211.NL80211_IFTYPE_STATION
        self.devidx = self.ipr.link_lookup(ifname=self.ifname)[0]
        
        self.changelist = []

    def iwif_find_up(self):
        iw_l = IW().get_interfaces_dump()
        for iwif in iw_l:
            self.iftype = iwif.get_attr('NL80211_ATTR_IFTYPE')

            if self.iftype == nl80211.NL80211_IFTYPE_P2P_DEVICE:
                print 'P2P_DEVICE skipping'
                continue
            
            # the interface index is the unique key
            self.devidx = iwif.get_attr('NL80211_ATTR_IFINDEX')
            print "IW IF: idx=%d name=%s mac=%s ssid=%s" % (self.devidx,
                                                            iwif.get_attr('NL80211_ATTR_IFNAME'), 
                                                            iwif.get_attr('NL80211_ATTR_MAC'), 
                                                            iwif.get_attr('NL80211_ATTR_SSID'))

            link = self.ipr.link('get', index=self.devidx)[0]
            if self.iftype == nl80211.NL80211_IFTYPE_STATION:
                if (link.get_attr('IFLA_OPERSTATE') == 'UP'):
                    print link['index'], link.get_attr('IFLA_IFNAME'), 'is UP'
                    addr_l = self.ipr.get_addr(family=AF_INET, index=self.devidx)
                    
                    for addr in addr_l:
                       print "IPv4 address list:", addr.get_attr('IFA_LABEL'), addr.get_attr('IFA_ADDRESS')
            elif self.iftype == nl80211.NL80211_IFTYPE_MONITOR:
                print link['index'], link.get_attr('IFLA_IFNAME'), 'is an rfmon link'
            else:
                print 'unknown iftype', self.iftype

    def is_linkup(self):
        link = self.ipr.link('get', index=self.devidx)[0]
        if link.get_attr('IFLA_OPERSTATE') == 'UP':
            return True
        else:
            return False
        
    def update(self, **keyargs):
        if 'mac' in keyargs:
            self.mac_addr.update(keyargs['mac'])
            if 'debug' in keyargs:
                print 'update mac=', keyargs['mac']
        if 'ip' in keyargs:
            self.ipv4_addr = ipaddress.IPv4Address(keyargs['ip'])
            if 'debug' in keyargs:
                print 'update ip=', keyargs['ip']
        self.changelist.extend(keyargs.keys())

    def __repr__(self):
        r = [str(self.mac_addr), self.ipv4_addr]
        return str(r)

    def _change_mac(self):

        try:
            # print '%s: set link to %s' % (self.ifname, str(self.mac_addr))

            # set link to a new MAC, it must be down first (root access)
            self.ipr.link('set', index=self.devidx, state='down')
            self.ipr.link('set', index=self.devidx, address=str(self.mac_addr))
            self.ipr.link('set', index=self.devidx, state='up')
        except (NetlinkError), e:
            print "link set:", e
            sys.exit(-1)

    def _change_ip(self):
        addrs = self.ipr.get_addr(family=AF_INET)
        self.ipr.flush_addr(index=self.devidx)
        # bp()
        self.ipr.addr('add', index=self.devidx, address=str(self.ipv4_addr), mask=24, broadcast='192.168.3.255')

    def commit(self):

        # check link is up
        if not self.is_linkup():
            print 'link down'
            return
        
        # save the default gw address before making changes
        route_l=self.ipr.get_default_routes(family=AF_INET)
        gw=route_l[0].get_attr('RTA_GATEWAY')
        
        if 'mac' in self.changelist:
            self._change_mac()
        if 'ip' in self.changelist:
            self._change_ip()

        # need to restore default route to gateway when changing MAC or IP
        self.ipr.route('add', gateway=gw)

class TestNetProbe(unittest.TestCase):

    def setUp(self):
        '''
        make sure network is connected then create test values
        '''
        self._check_url()
        self.np = NetProbe()
        self.testmac = MAC_addr(mac='fe:ed:be:ef:05:01')
        self.testip = ipaddress.IPv4Address('192.168.3.108')
        
    def tearDown(self):
        pass

    def _check_url(self):
        '''
        Probe connectivity to internet
        https://docs.python.org/2/library/urllib2.html
        '''
        EXSITE='http://www.google.com'
        print 'Send HTTP request to', EXSITE
        try:
            f = urllib2.urlopen(EXSITE)
        except IOError, e:
            print 'Fail to connect:', e
            raise IOError
        except:
            raise ValueError

        code = f.getcode()
        self.assertEqual(f.getcode(), 200, 'bad response code')
        rsp = f.read()
        rlen = len(rsp)
        self.assertTrue(rlen>10000, format('bad response size=%d' % rlen) )
        print 'success response code=%d len=%d' % (code, rlen)

    def test_setup(self):
        '''empty test for setup'''
        pass
        
    @unittest.skip('good')
    def test_mac1(self):
        self.np.update(mac=str(self.testmac))
        self.np.commit()
        self._check_url()

    @unittest.skip('good')
    def test_mac2(self):
        print 'testmac+4'
        self.testmac.inc(4)
        self.np.update(mac=str(self.testmac))
        self.np.commit()
        self._check_url()

    @unittest.skip('good')
    def test_ip1(self):
        self.np.update(ip=str(self.testip))
        self.np.commit()
        self._check_url()

    @unittest.skip('good')
    def test_ipmac1(self):
        self.testip=self.testip+3
        self.testmac.inc(18)
        print 'mac=', self.testmac, 'ip=', self.testip

        self.np.update(ip=str(self.testip), mac=str(self.testmac))
        self.np.commit()
        self._check_url()

    def test_ipmac5(self):
        mac_l = MAC_addr();
        ip_l = ipaddress.IPv4Address('192.168.3.80')
        for i in range(1,5):
            print 'Update mac=', mac_l, 'ip=', ip_l
            self.np.update(mac=str(mac_l), ip=str(ip_l))
            self.np.commit()
            # delay for wpa to associate and authenticate
            # FIXME: check link status (iw dev $IF link)
            sleep(4)
            self._check_url()
            mac_l.inc(0x2)
            ip_l += 1
        
if __name__ == '__main__':
    unittest.main()
