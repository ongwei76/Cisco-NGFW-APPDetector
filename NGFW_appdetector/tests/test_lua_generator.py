from ngfw_appdetector.lua_generator import FingerprintAggregator, LuaRenderer
from ngfw_appdetector.models import CorrelatedSample, FiveTuple, LocalFlow, NgfwEvent
from datetime import datetime, timezone


def _sample(sni="example.com", host="example.com", ua="MyApp/1.0"):
    t = datetime.now(timezone.utc)
    ft = FiveTuple(src_ip="10.0.0.1", src_port=1111, dst_ip="1.2.3.4", dst_port=443, proto="tcp")
    return CorrelatedSample(
        local=LocalFlow(five_tuple=ft, first_seen=t, last_seen=t, pid=1, process_name="MyApp"),
        ngfw=NgfwEvent(event_id="e1", timestamp=t, five_tuple=ft, tls_sni=sni, http_host=host, http_user_agent=ua),
    )


def test_aggregate_and_render(tmp_path):
    agg = FingerprintAggregator(min_samples=2)
    agg.add(_sample(sni="a.example.com"))
    agg.add(_sample(sni="b.example.com"))
    agg.add(_sample(sni="a.example.com"))

    ready = list(agg.ready())
    assert len(ready) == 1
    fp = ready[0]
    assert fp.app_name == "MyApp"
    assert "a.example.com" in fp.tls_snis and "b.example.com" in fp.tls_snis
    assert fp.sample_count == 3

    renderer = LuaRenderer(tmp_path)
    out = renderer.render(fp, app_id=1000001)
    text = out.read_text()
    assert "DetectorPackageInfo" in text
    assert "a.example.com" in text
    assert "MyApp" in text
    assert '"a.example.com"' in text
    assert 'gDetector:open_createApp("MyApp")' in text
    assert "gDetector:addSSLCertPattern(0, gAppId, host)" in text
    assert "gDetector:addSSLCnamePattern(0, gAppId, host)" in text
    assert 'gDetector:addAppUrl(0, 0, 0, gAppId, 0, host, "/", "http:", "", gAppId)' in text
    assert "1000001" not in text
    assert "addHostPortApp" not in text
    assert "setDetectorPackageInfo" not in text
    assert "validate" not in text
    assert text.isascii()


def test_render_deduplicates_tunnel_hosts(tmp_path):
    agg = FingerprintAggregator(min_samples=1)
    agg.add(_sample(sni="kong.example.com", host="kong.example.com"))
    agg.add(_sample(sni="api.example.com", host="API.example.com"))

    fp = next(iter(agg.ready()))
    text = LuaRenderer(tmp_path).render(fp).read_text()
    block = text.split("gHostPatternList = {", 1)[1].split("}", 1)[0]
    assert block.count('"kong.example.com"') == 1
    assert block.casefold().count('"api.example.com"') == 1
