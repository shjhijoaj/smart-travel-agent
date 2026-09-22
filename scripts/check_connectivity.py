"""No credentials printed: compare environment proxy vs direct TLS."""
import asyncio
import httpx


async def main():
    async def probe(url, trust):
        try:
            async with httpx.AsyncClient(timeout=12, trust_env=trust) as client:
                r = await client.get(url)
                print(url.split('/')[2], 'environment' if trust else 'direct', r.status_code,
                      'bytes', len(r.content), flush=True)
        except Exception as e:
            print(url.split('/')[2], 'environment' if trust else 'direct', type(e).__name__, flush=True)
    await asyncio.gather(*(probe(url, trust) for url in (
        'https://geocoding-api.open-meteo.com/v1/search?name=Hangzhou&count=1',
        'https://api.open-meteo.com/v1/forecast?latitude=30.27&longitude=120.15&daily=temperature_2m_max&timezone=auto',
        'https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull',
    ) for trust in (True, False)))


if __name__ == '__main__':
    asyncio.run(main())
