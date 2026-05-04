import unittest

import argus.application as application
import argus.application.packs as application_packs
import argus.capability_packs as capability_packs
import argus.capability_packs.advice as pack_advice
import argus.capability_packs.checking as pack_checking
import argus.capability_packs.creation as pack_creation
import argus.capability_packs.models as pack_models
import argus.capability_packs.roles as pack_roles
import argus.capability_packs.stores as pack_stores
import argus.governance as governance
import argus.governance.models as governance_models
import argus.governance.reporting as governance_reporting


class StructureBoundariesTest(unittest.TestCase):
    def test_large_domain_areas_are_packages_with_compatibility_exports(self):
        self.assertTrue(hasattr(application, "__path__"))
        self.assertTrue(hasattr(capability_packs, "__path__"))
        self.assertTrue(hasattr(governance, "__path__"))
        self.assertTrue(hasattr(capability_packs, "CapabilityPackCreator"))
        self.assertTrue(hasattr(capability_packs, "RolePackStore"))
        self.assertTrue(hasattr(governance, "GovernanceReporter"))
        self.assertTrue(hasattr(application, "GovernanceApplication"))

    def test_domain_packages_expose_responsibility_modules(self):
        self.assertIs(application_packs.CapabilityPackApplication, application.CapabilityPackApplication)
        self.assertIs(pack_models.CapabilityPackManifest, capability_packs.CapabilityPackManifest)
        self.assertIs(pack_creation.CapabilityPackCreator, capability_packs.CapabilityPackCreator)
        self.assertIs(pack_checking.CapabilityPackChecker, capability_packs.CapabilityPackChecker)
        self.assertIs(pack_stores.CapabilityPackStore, capability_packs.CapabilityPackStore)
        self.assertIs(pack_roles.RolePackStore, capability_packs.RolePackStore)
        self.assertIs(pack_advice.CapabilityPackAdvisor, capability_packs.CapabilityPackAdvisor)
        self.assertIs(governance_models.GovernanceFinding, governance.GovernanceFinding)
        self.assertIs(governance_reporting.GovernanceReporter, governance.GovernanceReporter)


if __name__ == "__main__":
    unittest.main()
