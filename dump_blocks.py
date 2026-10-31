import zipfile
import xml.etree.ElementTree as ET

z = zipfile.ZipFile('phase6_chatgpt_regerative.slx')
root_xml = z.read('simulink/systems/system_root.xml').decode('utf-8', errors='ignore')
root = ET.fromstring(root_xml)

with open('slx_blocks_full.txt', 'w', encoding='utf-8') as f:
    for b in root.findall('.//Block'):
        sid = b.attrib.get('SID')
        name = b.attrib.get('Name')
        btype = b.attrib.get('BlockType')
        f.write(f"[{sid}] {btype}: {name}\n")
        for p in b.findall('P'):
            f.write(f"    {p.attrib.get('Name')}: {p.text}\n")
        for inst in b.findall('.//InstanceData'):
            for p in inst.findall('P'):
                f.write(f"    inst {p.attrib.get('Name')}: {p.text}\n")
        f.write("\n")

print("Wrote slx_blocks_full.txt successfully.")
