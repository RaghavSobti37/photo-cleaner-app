import { createZip, groupByExactHash, groupSimilarHashes, selectBestImage } from './photo-cleaner.js';

const MAX_FILES = 50;
const MAX_FILE_BYTES = 20 * 1024 * 1024;
const input = document.querySelector('#photos');
const threshold = document.querySelector('#threshold');
const thresholdValue = document.querySelector('#threshold-value');
const run = document.querySelector('#run');
const status = document.querySelector('#status');
const results = document.querySelector('#results');
const download = document.querySelector('#download');
let finalSelection = [];

function setStatus(message, type = '') {
  status.textContent = message;
  status.className = type;
}

function readableBytes(bytes) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function hashFile(file) {
  const bitmap = await createImageBitmap(file);
  const size = 8;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext('2d', { willReadFrequently: true });
  context.drawImage(bitmap, 0, 0, size, size);
  const pixels = context.getImageData(0, 0, size, size).data;
  const brightness = [];
  for (let index = 0; index < pixels.length; index += 4) {
    brightness.push((pixels[index] * 0.299) + (pixels[index + 1] * 0.587) + (pixels[index + 2] * 0.114));
  }
  const average = brightness.reduce((sum, value) => sum + value, 0) / brightness.length;
  bitmap.close();
  return brightness.map((value) => (value >= average ? '1' : '0')).join('');
}

function renderResults(images, exactGroups, similarGroups) {
  results.replaceChildren();
  const summary = document.createElement('p');
  summary.textContent = `Keeping ${images.length} photo${images.length === 1 ? '' : 's'} · ${exactGroups.length} exact duplicate group${exactGroups.length === 1 ? '' : 's'} · ${similarGroups.length} similar group${similarGroups.length === 1 ? '' : 's'}.`;
  results.append(summary);
  for (const image of images) {
    const card = document.createElement('article');
    const preview = document.createElement('img');
    preview.src = URL.createObjectURL(image.file);
    preview.alt = image.file.name;
    preview.onload = () => URL.revokeObjectURL(preview.src);
    const label = document.createElement('p');
    label.textContent = `${image.file.name} · ${image.width}×${image.height}`;
    card.append(preview, label);
    results.append(card);
  }
}

async function processPhotos() {
  const files = [...input.files];
  if (!files.length) return setStatus('Choose photos first.', 'error');
  if (files.length > MAX_FILES) return setStatus(`Choose at most ${MAX_FILES} photos at once.`, 'error');
  const invalid = files.find((file) => !file.type.startsWith('image/') || file.size > MAX_FILE_BYTES);
  if (invalid) return setStatus(`${invalid.name} is not a supported image or exceeds ${readableBytes(MAX_FILE_BYTES)}.`, 'error');

  run.disabled = true;
  download.hidden = true;
  setStatus('Reading photos locally…');
  try {
    const images = [];
    for (const [index, file] of files.entries()) {
      setStatus(`Analysing ${index + 1} of ${files.length} locally…`);
      const bitmap = await createImageBitmap(file);
      const image = { id: `${file.name}-${index}`, file, width: bitmap.width, height: bitmap.height, hash: await hashFile(file) };
      bitmap.close();
      images.push(image);
    }
    const exactGroups = groupByExactHash(images);
    const exactBest = exactGroups.map(selectBestImage);
    const exactMembers = new Set(exactGroups.flat());
    const candidates = [...exactBest, ...images.filter((image) => !exactMembers.has(image))];
    const similarGroups = groupSimilarHashes(candidates, Number(threshold.value));
    const similarBest = similarGroups.map(selectBestImage);
    const similarMembers = new Set(similarGroups.flat());
    finalSelection = [...similarBest, ...candidates.filter((image) => !similarMembers.has(image))];
    renderResults(finalSelection, exactGroups, similarGroups);
    download.hidden = false;
    setStatus('Done. Photos never left this browser.', 'success');
  } catch (error) {
    console.error(error);
    setStatus(`Could not analyse photos: ${error.message}`, 'error');
  } finally {
    run.disabled = false;
  }
}

threshold.addEventListener('input', () => { thresholdValue.textContent = threshold.value; });
run.addEventListener('click', processPhotos);
download.addEventListener('click', async () => {
  const zip = await createZip(finalSelection.map((image) => image.file));
  const link = document.createElement('a');
  link.href = URL.createObjectURL(zip);
  link.download = 'cleaned-photos.zip';
  link.click();
  URL.revokeObjectURL(link.href);
});
