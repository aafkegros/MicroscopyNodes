import os

os.environ["MIN_TEST"] = "1"

from microscopynodes.data_model import (
    ChannelDataModel,
    ChannelModel,
    ChannelVizModel,
    DatasetModel,
)
from microscopynodes.ui import preferences


def _channel(ix, source_name=None):
    return ChannelModel(
        cache_path="",
        source_name=source_name,
        data=ChannelDataModel(
            dataset_resolution=0,
            ix=ix,
            axes_order="zyx",
            source_axes_order="czyx",
            unit="MICROMETER",
            source="test.tif",
        ),
        viz=ChannelVizModel(ix=ix),
    )


def test_import_defaults_revolve_visualization_without_repeating_names():
    dataset = DatasetModel(channels=[_channel(ix) for ix in range(3)])
    defaults = [
        ChannelVizModel(ix=0, name="DNA", volume=False, surface=True),
        ChannelVizModel(ix=1, name="Membrane", emission=False),
    ]

    dataset.apply_viz_defaults(defaults)

    assert dataset.channels[0].viz.name == "DNA"
    assert dataset.channels[0].viz.surface is True
    assert dataset.channels[1].viz.name == "Membrane"
    assert dataset.channels[1].viz.emission is False
    assert dataset.channels[2].viz.name == "Channel 2"
    assert dataset.channels[2].viz.surface is True
    assert dataset.channels[2].viz.ix == 2


def test_source_metadata_name_takes_precedence_over_preference_name():
    dataset = DatasetModel(channels=[_channel(0, source_name="DAPI")])

    dataset.apply_viz_defaults([
        ChannelVizModel(ix=0, name="Configured name", volume=False),
    ])

    assert dataset.channels[0].viz.name == "DAPI"
    assert dataset.channels[0].viz.volume is False


def test_preferences_fall_back_for_restricted_context(monkeypatch):
    class RestrictedContext:
        @property
        def preferences(self):
            raise RuntimeError("context is restricted")

    monkeypatch.setattr(preferences, "DEFAULT_PREFERENCES", None)

    fallback = preferences.addon_preferences(RestrictedContext())

    assert len(fallback.channels) == fallback.n_default_channels
