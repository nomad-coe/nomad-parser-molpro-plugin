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

from xml.etree import ElementTree as ET
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.basesections import System
from nomad.datamodel.metainfo.simulation.run import Program, Run
from nomad.datamodel.metainfo.simulation.system import Atoms, AtomsGroup
from nomad.parsing.parser import Parser


class MolproXMLOutParser(Parser):
    def __init__(self):
        self._root = ET.parse(mainfile).getroot()
        pass

    @property
    def program(self) -> Program:
        """Parse the program from the xml file."""
        program: Program = Program()
        program.name = "Molpro"
        version_tag = self._root.iter["version"]
        program.version = version_tag.text()
        program.version_internal = version_tag.attrib["SHA"]
        # program.compilation_datetime?
        return program

    @property
    def atoms(self) -> Atoms:
        """Parse the atoms from the xml file."""
        atoms: Atoms = Atoms()

        for atom in self._root.iter("cml:atom"):
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
        for atom in self._root.iter("cml:atom"):
            connectivity.atom_indices.append(convert_id(atom.attrib["id"]))
        for bond in self._root.iter("cml:bond"):
            connectivity.bonds.append(
                [convert_id(x) for x in bond.attrib["atomRefs2"].split()]
            )

        return connectivity

    def parse(self, mainfile: str, archive: EntryArchive, logger) -> EntryArchive:
        """Build up the archive from pre-defined sections."""
        self.archive = archive
        self.logger = logger

        self.archive.run.append(Run())
        self.archive.run[0].program = self.program
        system = System(atoms=self.atoms, atoms_group=self.connectivity)
        self.archive.run[0].system.append(system)

        return self.archive
