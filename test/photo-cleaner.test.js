import test from 'node:test';
import assert from 'node:assert/strict';
import { createZip, groupByExactHash, groupSimilarHashes, hammingDistance, selectBestImage } from '../web/photo-cleaner.js';

test('hammingDistance counts changed bits', () => {
  assert.equal(hammingDistance('0000', '0011'), 2);
});

test('groupByExactHash returns only duplicate groups', () => {
  const images = [
    { id: 'a', hash: '1010', width: 100, height: 100 },
    { id: 'b', hash: '1010', width: 200, height: 100 },
    { id: 'c', hash: '1111', width: 100, height: 100 },
  ];
  assert.deepEqual(groupByExactHash(images).map(group => group.map(image => image.id)), [['a', 'b']]);
});

test('groupSimilarHashes groups matching photos but leaves unique photos alone', () => {
  const images = [
    { id: 'a', hash: '00000000' },
    { id: 'b', hash: '00000001' },
    { id: 'c', hash: '11111111' },
  ];
  assert.deepEqual(groupSimilarHashes(images, 1).map(group => group.map(image => image.id)), [['a', 'b']]);
});

test('selectBestImage retains highest-resolution image', () => {
  const best = selectBestImage([
    { id: 'small', width: 800, height: 600 },
    { id: 'large', width: 1600, height: 1200 },
  ]);
  assert.equal(best.id, 'large');
});

test('createZip returns a valid ZIP signature', async () => {
  const zip = await createZip([new File(['hello'], 'kept.txt', { type: 'text/plain' })]);
  assert.deepEqual([...new Uint8Array(await zip.slice(0, 4).arrayBuffer())], [80, 75, 3, 4]);
});
