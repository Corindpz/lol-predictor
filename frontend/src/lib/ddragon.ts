let _version = "15.8.1";
let _fetched = false;

export function champIcon(name: string): string {
  return `https://ddragon.leagueoflegends.com/cdn/${_version}/img/champion/${name}.png`;
}

export async function initDDragon(): Promise<void> {
  if (_fetched) return;
  _fetched = true;
  try {
    const versions: string[] = await fetch(
      "https://ddragon.leagueoflegends.com/api/versions.json"
    ).then(r => r.json());
    _version = versions[0];
  } catch {}
}
