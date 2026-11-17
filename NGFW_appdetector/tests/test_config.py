from ngfw_appdetector.config import AppConfig, FmcConfig, load_config, save_fmc_section


def test_load_config_accepts_utf8_bom(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        "fmc:\n  host: 198.51.100.10\n  username: admin\n",
        encoding="utf-8-sig",
    )

    loaded = load_config(config)

    assert loaded.fmc.host == "198.51.100.10"
    assert loaded.fmc.username == "admin"


def test_save_fmc_section_writes_utf8_without_bom(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("generator:\n  min_samples: 5\n", encoding="utf-8-sig")

    save_fmc_section(
        config,
        FmcConfig(host="fmc.example.test", username="测试用户", password="secret"),
    )

    raw = config.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert load_config(config).fmc.username == "测试用户"
    assert load_config(config).generator.min_samples == 5


def test_capture_defaults_to_thirty_second_fmc_drain() -> None:
    assert AppConfig().capture.fmc_drain_sec == 30
