about_conf = configuration_data()
about_conf.set('VERSION', meson.project_version())
about_conf.set('AUTHORS', authors)
about_conf.set('APPID', project_id)
about_conf.set('COPYRIGHT', copyright)
about_conf.set('PURL', package_url)

gnome.compile_resources(
  'mushroom',
  'mushroom.gresource.xml',
  gresource_bundle: true,
  source_dir: meson.current_build_dir(),
  install_dir: pkgdatadir,
  install: true,
  dependencies: configure_file (
    input: 'about.ui.in',
    output: '@BASENAME@',
    configuration: about_conf
  )
)
