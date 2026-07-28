export function formatChunkDimensions(config: {
  chunk_size: number;
  overlap: number;
  padding?: number;
}): string {
  return `${config.chunk_size}/${config.overlap}/${config.padding ?? 0}`;
}
