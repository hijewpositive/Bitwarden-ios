#!/usr/bin/env python3
"""Static guard for the TOTP picker's column wiring; not a rendered UI test."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
VIEW = ROOT / 'BitwardenShared/UI/Vault/Vault/VaultItemSelection/VaultItemSelectionView.swift'


class PickerLayoutContractTests(unittest.TestCase):
    def test_searchable_content_is_in_centered_adaptive_column(self):
        source = VIEW.read_text()
        searchable = source.split('private struct VaultItemSelectionSearchableView: View {', 1)[1]
        body = searchable.split('    // MARK: Private Views', 1)[0]
        # This checks wiring, not actual geometry, hit testing, or behavior.
        self.assertIn('GeometryReader { geometry in', body)
        self.assertIn('.frame(width: VaultListContentLayout.contentWidth(for: geometry.size.width))', body)
        self.assertIn('.frame(maxWidth: .infinity, maxHeight: .infinity)', body)
        self.assertLess(body.index('contentView()'), body.index('searchContentView()'))
        self.assertLess(body.index('searchContentView()'), body.index('.frame(width: VaultListContentLayout'))
        self.assertLess(body.index('addItemFloatingActionButton'), body.index('.frame(width: VaultListContentLayout'))


if __name__ == '__main__':
    unittest.main()
