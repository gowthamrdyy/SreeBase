// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  tutorialSidebar: [
    'index',
    'faq',
    'roadmap',
    'about',
    {
      type: 'category',
      label: 'Get Started',
      collapsed: false,
      items: [
        'tutorials/index',
        'tutorials/installation',
        'tutorials/first-database',
        'tutorials/concepts',
      ],
    },
    {
      type: 'category',
      label: 'Query Language',
      items: [
        'syntax',
        'tutorials/insert',
        'tutorials/read',
        'tutorials/update',
        'tutorials/delete',
        'tutorials/aggregations',
        'tutorials/indexes',
      ],
    },
    {
      type: 'category',
      label: 'Build Apps',
      items: [
        'api',
        'tutorials/example-app',
      ],
    },
    {
      type: 'category',
      label: 'Operations',
      items: [
        'tutorials/security',
        'tutorials/storage',
        'tutorials/troubleshooting',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'tutorials/cheat-sheet',
      ],
    },
  ],
};

export default sidebars;
