export function hammingDistance(first, second) {
  if (first.length !== second.length) throw new Error('Image hashes must have the same length.');
  let distance = 0;
  for (let index = 0; index < first.length; index += 1) {
    if (first[index] !== second[index]) distance += 1;
  }
  return distance;
}

export function groupByExactHash(images) {
  const groups = new Map();
  for (const image of images) {
    const group = groups.get(image.hash) ?? [];
    group.push(image);
    groups.set(image.hash, group);
  }
  return [...groups.values()].filter((group) => group.length > 1);
}

export function groupSimilarHashes(images, threshold = 5) {
  const remaining = new Set(images.map((_, index) => index));
  const groups = [];
  for (let index = 0; index < images.length; index += 1) {
    if (!remaining.has(index)) continue;
    const group = [images[index]];
    remaining.delete(index);
    for (let candidate = index + 1; candidate < images.length; candidate += 1) {
      if (!remaining.has(candidate)) continue;
      if (hammingDistance(images[index].hash, images[candidate].hash) <= threshold) {
        group.push(images[candidate]);
        remaining.delete(candidate);
      }
    }
    if (group.length > 1) groups.push(group);
  }
  return groups;
}

export function selectBestImage(images) {
  return images.reduce((best, image) => (
    image.width * image.height > best.width * best.height ? image : best
  ));
}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function uint16(value) {
  return new Uint8Array([value & 255, (value >>> 8) & 255]);
}

function uint32(value) {
  return new Uint8Array([value & 255, (value >>> 8) & 255, (value >>> 16) & 255, (value >>> 24) & 255]);
}

function joinBytes(parts) {
  const length = parts.reduce((total, part) => total + part.length, 0);
  const result = new Uint8Array(length);
  let offset = 0;
  for (const part of parts) {
    result.set(part, offset);
    offset += part.length;
  }
  return result;
}

export async function createZip(files) {
  const encoder = new TextEncoder();
  const localFiles = [];
  const centralFiles = [];
  let offset = 0;
  for (const file of files) {
    const name = encoder.encode(file.name);
    const contents = new Uint8Array(await file.arrayBuffer());
    const crc = crc32(contents);
    const local = joinBytes([
      uint32(0x04034b50), uint16(20), uint16(0), uint16(0), uint16(0), uint16(0),
      uint32(crc), uint32(contents.length), uint32(contents.length), uint16(name.length), uint16(0), name, contents,
    ]);
    const central = joinBytes([
      uint32(0x02014b50), uint16(20), uint16(20), uint16(0), uint16(0), uint16(0), uint16(0),
      uint32(crc), uint32(contents.length), uint32(contents.length), uint16(name.length), uint16(0), uint16(0),
      uint16(0), uint16(0), uint32(0), uint32(offset), name,
    ]);
    localFiles.push(local);
    centralFiles.push(central);
    offset += local.length;
  }
  const centralDirectory = joinBytes(centralFiles);
  const end = joinBytes([
    uint32(0x06054b50), uint16(0), uint16(0), uint16(files.length), uint16(files.length),
    uint32(centralDirectory.length), uint32(offset), uint16(0),
  ]);
  return new Blob([...localFiles, centralDirectory, end], { type: 'application/zip' });
}
