project('mushroom',
          version: '0.2.0-alpha',
    meson_version: '>= 0.59.0',
  default_options: [ 'warning_level=2',
                     'werror=false',
                   ],
)

i18n = import('i18n')

gnome = import('gnome')

python = import('python')


python_bin = python.find_installation('python3', modules: 'pytube')

project_id = 'com.github.azab246.mushroom'
project_name = 'Mushroom'
package_url = 'https://github.com/azab246/Mushroom'
copyright = '© 2022 Abdalrahman Azab.'
authors = 'Abdalrahman Azab'
pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())

dependencies = [
	dependency('gtk4', version: '>=4.6.0'),
	dependency('libadwaita-1', version: '>=1.2.alpha'),
]

subdir('data')
subdir('src/gtk')
subdir('src')
subdir('po')

gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
