#!/usr/bin/env python
"""
IEEE
* MAC class

a) Each address field shall be 48 bits in length. While IEEE 802 specifies the use of either 16- or 48-bit
addresses, no conformant implementation of IEEE 802.3 uses 16-bit addresses. The use of 16-bit
addresses is specifically excluded by this standard.
b) The first bit (LSB) shall be used in the Destination Address field as an address type designation bit to
identify the Destination Address either as an individual or as a group address. If this bit is 0, it shall
indicate that the address field contains an individual address. If this bit is 1, it shall indicate that the
address field contains a group address that identifies none, one or more, or all of the stations con-
nected to the LAN. In the Source Address field, the first bit is reserved and set to 0.
c) The second bit shall be used to distinguish between locally or globally administered addresses. For
globally administered (or U, universal) addresses, the bit is set to 0. If an address is to be assigned
locally, this bit shall be set to 1. Note that for the broadcast address, this bit is also a 1.
d) Each octet of each address field shall be transmitted least significant bit first.

Ethernet (802.3)

"""

import unittest
from pdb import set_trace as bp

class MAC_addr(object):
    '''IEEE Media Access Control Address Factory
    b0: 0 for unicast
    b1: 1 for locally administered address
    For local MAC the lower nibble of first octet: 0x2, 0x6, 0xa, 0xe
    LSB of each octet is put on wire first
    0xfe = b11111110 is sent as 01111111

    See http://standards-oui.ieee.org/oui.txt for globally assigned MAC ranges.  
    All must have the low-order nibble set to 0x0, 0x4, 0x8, 0xc
    For example, one OUI assigned to Cisco Systems is 38-1C-1A
    0x38 = b00111000 is sent as 00011100
    '''

    # default MAC address
    default_addr = 0xfeedbeef0401
    
    def __init__(self, **keyargs):
        if 'mac' in keyargs:
            tmp=keyargs['mac']
            # remove separators
            for char in '-:':
                tmp=tmp.translate(None,char)
            if len(tmp) != 12:
                raise ValueError
            self.addr = int(tmp, 16)
            self.verify()
        else:
            self.addr = MAC_addr.default_addr

    def __repr__(self):
        xs='{:012x}'.format(self.addr)
        return ':'.join(xs[i:i+2] for i in range(0, len(xs), 2))

    def verify(self):
        '''verify this is a valid MAC'''
        #bp()
        pass

    def update(self, mac=''):
        tmp=mac
        for char in '-:':
            tmp=tmp.translate(None,char)
        self.addr = int(tmp, 16)
        self.verify()

    def inc(self, val):
        self.addr += val

    def dec(self, val):
        self.addr -= val

    def get(self):
        return self.addr

    def getstr(self, join_char=''):
        '''
        convert MAC to a string with bytes separated by join_char
        '''
        xs='{:012x}'.format(self.addr)
        if join_char:
            xs=join_char.join(xs[i:i+2] for i in range(0, len(xs), 2))
        return xs

class TestMAC(unittest.TestCase):

    def setUp(self):
        '''create valid mac addresses'''
        self.macdef = MAC_addr()
        self.mac1 = MAC_addr(mac='fe:ed:be:ef:04:0a')
        self.mac2 = MAC_addr(mac='01:02:03:04:05:06')
        self.mac3 = MAC_addr(mac='00:00:00:00:01:02')

    def tearDown(self):
        pass

    def test_get(self):
        '''check all have expected values'''
        self.assertEqual(self.macdef.get(), MAC_addr.default_addr)
        self.assertEqual(self.mac1.get(), 0xfeedbeef040a)
        self.assertEqual(self.mac2.get(), 0x010203040506)
        self.assertEqual(self.mac3.get(), 0x0102)

    def test_str(self):
        self.assertEqual(str(self.mac1), 'fe:ed:be:ef:04:0a')
    
    def test_getstr(self):

        self.assertEqual(self.mac1.getstr(), 'feedbeef040a', 'mac1 fail no-colon')
        self.assertEqual(self.mac2.getstr(), '010203040506', 'mac2 fail no-colon')
        self.assertEqual(self.mac2.getstr(':'), '01:02:03:04:05:06', 'mac2 fail colon')
        self.assertEqual(self.mac3.getstr('-'), '00-00-00-00-01-02', 'mac3 fail hyphen')
        
    def test_inc(self):
        self.macdef.inc(0x1)
        self.assertEqual(self.macdef.getstr(':'), 'fe:ed:be:ef:04:02', 'macdef inc 0x1')
        self.macdef.inc(0x8)
        self.assertEqual(self.macdef.getstr(':'), 'fe:ed:be:ef:04:0a', 'macdef inc 0x8')
        self.mac2.inc(0x100)
        self.assertEqual(self.mac2.getstr(':'), '01:02:03:04:06:06', 'mac2 inc 0x100')
        self.mac2.inc(2)
        self.assertEqual(self.mac2.getstr('-'), '01-02-03-04-06-08', 'mac2 inc 2')

    @unittest.expectedFailure
    def test_bad1(self):
        '''bad MAC address size'''
        badmac = MAC_addr(mac='fe:ed:be:ef')

    @unittest.expectedFailure
    def test_bad2(self):
        '''bad MAC address value'''
        badmac = MAC_addr(mac='fe:gd:be:ef:01:01')

# unit testing...    
if __name__ == '__main__':
    unittest.main()
