#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD.
# See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import os
from typing import Iterable, Optional, Union
from xml.etree import ElementTree as ET
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.simulation.run import Program, Run
from nomad.datamodel.metainfo.simulation.system import System, Atoms, AtomsGroup
from nomad.metainfo import Quantity, Package


m_package = Package()


class MolproXMLOutParser:
    def find_tags(self, tag_name: str, element=None, results=None) -> list:
        if element is None:
            element = self._root
        if results is None:
            results = []
        # Check if the current element matches the tag_name
        if element.tag.endswith(tag_name):
            results.append(element)
        # Recursively search in child elements
        for child in element:
            self.find_tags(tag_name, child, results)
        return results

    # TODO: consider storing deeply nested tags upon extraction
    def extracted_atoms(self):
        if not hasattr(self, "_extracted_atoms"):
            self._extracted_atoms = self.find_tags("atom")
        return self._extracted_atoms

    @property
    def program(self) -> Program:
        """Parse the program from the xml file."""
        program: Program = Program()
        program.name = "Molpro"
        version_tag = self.find_tags("version")[0]
        try:
            program.version = (
                f'{version_tag.attrib["major"]}.{version_tag.attrib["minor"]}'
            )
            program.version_internal = version_tag.attrib["SHA"]
            # program.compilation_datetime?
        except KeyError:
            self.logger.warning("Could not parse Molpro version information.")
        return program

    @property
    def atoms(self) -> Atoms:
        """Parse the atoms from the xml file."""
        atoms: Atoms = Atoms()

        if len(self.extracted_atoms()):
            atoms.labels, atoms.positions = [], []
            for atom in self.find_tags("atom"):
                atoms.labels.append(atom.attrib["elementType"])
                atoms.positions.append(
                    [float(atom.attrib[f"{x}3"]) for x in ["x", "y", "z"]]
                )

        return atoms

    @property
    def connectivity(self) -> AtomsGroup:  # TODO: abstract out to any kind of `System`
        """Parse the atom indices and bonds for the entire system."""
        connectivity: AtomsGroup = AtomsGroup()

        convert_id = lambda x: int(x[1:])  # id-format: "a1" -> 1
        connectivity.label = "all"
        for atom in self.find_tags("atom"):
            connectivity.atom_indices.append(convert_id(atom.attrib["id"]))
        for bond in self.find_tags("bond"):
            connectivity.bonds.append(
                [convert_id(x) for x in bond.attrib["atomRefs2"].split()]
            )

        return connectivity

    def parse(self, filepath: str, archive: EntryArchive, logger) -> EntryArchive:
        """Build up the archive from pre-defined sections."""
        self._root = ET.parse(filepath).getroot()
        self.logger = logger

        archive.run.append(Run())
        sec_run = archive.run[0]

        sec_run.program = self.program
        sec_run.system.append(System(atoms=self.atoms, atoms_group=[self.connectivity]))

        return archive


class MolproParser:
    def __init__(self):
        self.parser = MolproXMLOutParser()

    def parse(self, filepath: str, archive: EntryArchive, logger) -> EntryArchive:
        """Build up the archive from pre-defined sections."""
        return self.parser.parse(filepath, archive, logger)


m_package.__init_metainfo__()
