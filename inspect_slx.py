import zipfile
import xml.etree.ElementTree as ET

z = zipfile.ZipFile('phase6_chatgpt_regerative.slx')
root_xml = z.read('simulink/systems/system_root.xml').decode('utf-8', errors='ignore')
root = ET.fromstring(root_xml)

for b in root.findall('.//Block'):
    sid = b.attrib.get('SID')
    name = b.attrib.get('Name')
    btype = b.attrib.get('BlockType')
    if any(k in name.lower() for k in ['permanent', 'universal', 'rlc', 'three-phase', 'source', 'bridge', 'pmsm', 'vdc', 'motor', 'gain', 'profile']):
        print(f"=== [{sid}] {name} ({btype}) ===")
        for p in b.findall('P'):
            print(f"  {p.attrib.get('Name')}: {p.text}")
        for inst in b.findall('.//InstanceData'):
            for p in inst.findall('P'):
                print(f"  inst {p.attrib.get('Name')}: {p.text}")
