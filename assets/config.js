/*
  Site config: the ONLY file to edit when accounts are approved. No rebuild needed.
  Empty values = the slot renders nothing (no blank boxes, no placeholder links).
*/
window.SITE_CONFIG = {
  // Google AdSense publisher id, e.g. 'ca-pub-1234567890123456'. This site is affiliate-first; no ad slots are placed yet.
  ADSENSE_CLIENT: '',

  // Amazon Associates tracking id, e.g. 'samsites-20'. Empty = all "Check price on Amazon" buttons stay hidden.
  AMAZON_TAG: '',

  // Contact page. Set a HubSpot form id (portal 20693956) and/or an email address.
  HUBSPOT_PORTAL_ID: '20693956',
  HUBSPOT_FORM_ID: '9f5020df-cf22-4018-bac9-4a89f544e208',
  CONTACT_EMAIL: '',

  // Affiliate links per service (full tracking URL from Impact, CJ, FlexOffers, Partnerize, etc.).
  // Empty = the button links to the service's official site with no tracking and no "sponsored" label.
  AFFILIATE: {
    'netflix': '',
    'hulu': '',
    'disney-plus': '',
    'hbo-max': '',
    'peacock': '',
    'paramount-plus': '',
    'prime-video': '',
    'apple-tv': '',
    'youtube-tv': '',
    'sling-tv': '',
    'fubo': '',
    'philo': ''
  }
};
