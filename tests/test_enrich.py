import base64
import unittest
from unittest.mock import patch
from src.enrich import (
    enrich_periods, fetch_repository_details, iso_day, readme_highlights,
    safe_homepage, use_case_ja,
)


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError('HTTP error')
    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.paths = []
    def get(self, url, **kwargs):
        self.paths.append(url)
        return self.responses.get(url.rsplit('api.github.com', 1)[-1], FakeResponse(404))


class EnrichTests(unittest.TestCase):
    def test_readme_highlights_ignores_badges_and_code(self):
        md = '''# Project
![badge](https://img.shields.io/x)
A tool that brings secure, automated workflows to desktop applications.
It can coordinate several tasks without the user having to manually switch windows.

## Features
- **Local execution** for privacy-sensitive workflows
- Can integrate with multiple external tooling systems

```sh
rm -rf /tmp/not-actually-a-feature
```
'''
        parsed = readme_highlights(md)
        self.assertIn('secure, automated workflows', parsed['excerpt'])
        self.assertEqual(len(parsed['features']), 2)
        self.assertNotIn('rm -rf', str(parsed))

    def test_readme_table_and_navigation(self):
        md = """# Art
[English](x) · [日本語](x) · [German](x) · [French](x) · [Spanish](x)

This is a real product description about creating interactive designs with precise scene control.

## Features
| Feature | Preview |
| --- | --- |
| **Image to Location**<br>Compose a consistent setting for virtual actors. | Preview |
| **3D Image Compositing**<br>Layer images and backgrounds. | Preview |
"""
        parsed = readme_highlights(md)
        self.assertIn('real product description', parsed['excerpt'])
        self.assertIn('Image to Location', parsed['features'][0])
        self.assertEqual(len(parsed['features']), 2)

    def test_readme_structure_bullets(self):
        md = """# Plugins
A curated plugin directory for developer assistants and integrated workflows across multiple organizations.

## Structure
- **/plugins** - Internal extensions and integrations
- **/external_plugins** - Third-party plugins and custom tools
"""
        self.assertEqual(len(readme_highlights(md)['features']), 2)

    def test_invalid_repo_and_untrusted_website(self):
        session = FakeSession({})
        self.assertIsNone(fetch_repository_details('../../etc/passwd', session))
        self.assertEqual(session.paths, [])
        self.assertIsNone(safe_homepage('javascript:alert(1)'))
        self.assertIsNone(safe_homepage('https://user:pw@example.com/'))
        self.assertEqual(safe_homepage('https://example.com'), 'https://example.com')
        self.assertIsNone(iso_day('n/a'))

    def test_metadata_features_and_release(self):
        markdown = '## About\nAn official companion that helps build task automations across workspaces.\n\n## Features\n- Multi-workspace orchestration and coordination\n- Supports developer tools and task scheduling\n'
        base='/repos/team/awesome'
        api = {
            base: FakeResponse(payload={'full_name':'team/awesome','description':'Automated coding agents',
                   'license':{'spdx_id':'MIT'},'topics':['agents','cli'],'forks_count':123,
                   'stargazers_count':4567,'pushed_at':'2026-10-20T04:00:00Z',
                   'created_at':'2025-09-05T00:00:00Z','homepage':'https://example.com', 'archived':False}),
            base+'/readme':FakeResponse(payload={'encoding':'base64','content':base64.b64encode(markdown.encode()).decode()}),
            base+'/releases/latest':FakeResponse(payload={'tag_name':'v2.1','published_at':'2026-10-01T04:00:00Z',
              'html_url':'https://github.com/team/awesome/releases/tag/v2.1'}),
        }
        d = fetch_repository_details('team/awesome', FakeSession(api))
        self.assertEqual(d['stars_total'],4567)
        self.assertEqual(d['forks'],123)
        self.assertEqual(d['license'],'MIT')
        self.assertEqual(d['pushed_on'],'2026-10-20')
        self.assertEqual(d['latest_release']['tag'],'v2.1')
        self.assertEqual(len(d['readme_features']),2)

    def test_api_failure_is_not_fabricated(self):
        s=FakeSession({'/repos/o/r':FakeResponse(404)})
        self.assertIsNone(fetch_repository_details('o/r',s))

    def test_readme_not_required_for_metadata(self):
        s=FakeSession({'/repos/o/r':FakeResponse(payload={'full_name':'o/r','stargazers_count':50})})
        d=fetch_repository_details('o/r',s)
        self.assertEqual(d['stars_total'],50)
        self.assertIsNone(d['readme_excerpt'])

    def test_reuses_metadata_across_periods(self):
        p={name:{'repositories':[{'full_name':'org/a','stars_total':None}, {'full_name':'org/b'}]} for name in ('daily','weekly','monthly')}
        with patch('src.enrich.fetch_repository_details',side_effect=[{'stars_total':100},None]) as f:
            result=enrich_periods(p,object())
        self.assertEqual(result,{'requested':2,'enriched':1})
        self.assertEqual(f.call_count,2)
        self.assertEqual(p['weekly']['repositories'][0]['details']['stars_total'],100)
        self.assertNotIn('details',p['daily']['repositories'][1])

    def test_interpretation_only_when_specific(self):
        self.assertIn('応募書類', use_case_ja('AI job search, cover letters'))
        self.assertIsNone(use_case_ja('A cool new product'))

if __name__=='__main__':unittest.main()
