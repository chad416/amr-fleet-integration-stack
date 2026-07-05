# Versioned maps

`factory.pgm` and `factory.yaml` are deterministic derivatives of the Gazebo
factory world. Regenerate them after changing collision geometry:

```bash
ros2 run amr_navigation generate_factory_map.py \
  --world /path/to/amr_simulation/worlds/factory.sdf \
  --output-dir /path/to/amr_navigation/maps
```

The navigation contract test fails when the committed map no longer matches the
world geometry.
