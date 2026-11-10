export function withFacility(path: string, facilityId?: string) {
  if (!facilityId) return path;
  return path + (path.includes('?') ? '&' : '?') + 'facility_id=' + encodeURIComponent(facilityId);
}
