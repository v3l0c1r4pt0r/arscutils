#!/usr/bin/env python3
## \file rid2name.py
#  \brief Convert resource id to resource name
import os
import sys
import json
from arsc.arsc import *
from arsc.stringpool import ResStringPool_header

## \class Arsc
#  \brief High-level ARSC file handler
class Arsc:

    def __init__(self, arsc=None):
        if arsc is None:
            arsc = ResTable()

        ## ResTable instance. Low-level access to ARSC file contents
        self.arsc = arsc

    def from_bytes(b, little=True):
        arsc, b = ResTable.from_bytes(b)

        return Arsc(arsc), b

    def from_file(f):
        fp = os.open(f, os.O_RDONLY)
        if fp < 0:
            raise Exception('Opening failed')

        size = os.lseek(fp, 0, os.SEEK_END)
        if size < 0:
            raise Exception('Opening failed')

        os.lseek(fp, 0, os.SEEK_SET)
        b = os.read(fp, size)
        return Arsc.from_bytes(b)

    def _find_null_utf16(buf):
        for i in range(0, len(buf), 2):
            if buf[i:i+2] == b'\0\0':
                return i
        raise Exception('NULL-terminator not found')

    ## Converts UTF-16 string as bytes into Python string
    def utf16_to_str(buf):
        return buf[:Arsc._find_null_utf16(buf)].decode('utf-16')

    ## Finds package with given package ID
    def pid_to_package(self, pid):
        for pkg in self.arsc.packages:
            if pkg.header.id.integer == pid:
                return pkg
        raise Exception('Package with ID {} not found'.format(hex(pid)))

    def get_packages(self):
        ret = {}
        for pkg in self.arsc.packages:
            pkg_id = pkg.header.id.integer
            pkg_name = Arsc.utf16_to_str(pkg.header.name)
            ret[pkg_id] = pkg_name
        return ret

    def get_package_types(self, pkg):
        ret = {}
        for i, t in enumerate(pkg.typeStrings.strings):
            if pkg.typeStrings.header.flags == ResStringPool_header.Flags.UTF8_FLAG:
                typStr = t[2:-1].decode('utf-8').strip('\0')
            else:
                # TODO: verify
                typStr = t[2:-2].decode('utf-16').strip('\0')
            ret[i + 1] = typStr
        return ret

    ## Finds all keys contained in given type ID and package ID
    def get_package_type_keys(self, pid, tid):
        if tid < 1:
            raise Exception('Minimum ID of type is 1, {} given'.format(tid))
        pkg = self.pid_to_package(pid)

        # find typeSpec headers for given type and every type before
        this_typeSpec = pkg.types[tid-1][0].header
        past_typeSecs = []
        for i in range(tid - 1):
            typeSpec = pkg.types[i][0].header
            past_typeSecs.append(typeSpec)

        # compute range of strings, storing key names related to given TID
        first = 0
        for typeSpec in past_typeSecs:
            first += typeSpec.entryCount.integer
        last = first + this_typeSpec.entryCount.integer

        # find keyStrings
        keylist = pkg.keyStrings.strings[first:last]

        # create dict with key IDs as dict-keys
        keys = {}
        for i, key in enumerate(keylist):
            keyStr = None
            if pkg.keyStrings.header.flags == ResStringPool_header.Flags.UTF8_FLAG:
                keyStr = key[2:-1].decode('utf-8').strip('\0')
            else:
                keyStr = key[2:-2].decode('utf-16').strip('\0')
            keys[i] = keyStr
        return keys

    ## Finds name of resource of given ID
    def rid_to_name(self, pid, tid, kid):
        packages = self.get_packages()
        pkg = self.pid_to_package(pid)
        types = self.get_package_types(pkg)
        keys = self.get_package_type_keys(pid, tid)
        return packages[pid], types[tid], keys[kid]

def main(argv):
    if len(argv) <= 1:
        print('Usage: resources.py resources.arsc resource-id [fqdn|xml|json]')
        sys.exit(1)

    fname = argv[1]
    arsc, b = Arsc.from_file(fname)

    rid = int(argv[2], 0)
    pid = (rid & 0xff000000) >> 24
    tid = (rid & 0xff0000) >> 16
    kid = rid & 0xffff

    if len(argv) > 3:
        out = argv[3]
    else:
        out = 'fqdn'

    pkg, typ, key = arsc.rid_to_name(pid, tid, kid)
    if out == 'fqdn':
        print('{}.R.{}.{}'.format(pkg, typ, key))
    elif out == 'xmlid':
        print('@{}:{}/{}'.format(pkg, typ, key))
    elif out == 'json':
        on = {'package': pkg, 'type': typ, 'key': key}
        print(json.dumps(on))
    else:
        raise Exception('Unknown output type: {}'.format(out))

if __name__ == '__main__':
    main(sys.argv)
